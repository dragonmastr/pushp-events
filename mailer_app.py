import csv
import mimetypes
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
import smtplib
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
LOG_DIR = BASE_DIR / "data" / "send_logs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class JobState:
    status: str = "idle"
    message: str = ""
    total: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    current: str = ""
    started_at: str = ""
    finished_at: str = ""
    log_path: str = ""
    stop_requested: bool = False


state = JobState()
state_lock = threading.Lock()
job_thread: threading.Thread | None = None


@app.route("/")
def index():
    return render_template("mailer.html")


@app.route("/status")
def status():
    with state_lock:
        payload = {
            "status": state.status,
            "message": state.message,
            "total": state.total,
            "sent": state.sent,
            "failed": state.failed,
            "skipped": state.skipped,
            "current": state.current,
            "started_at": state.started_at,
            "finished_at": state.finished_at,
            "log_path": state.log_path,
            "stop_requested": state.stop_requested,
        }
    return jsonify(payload)


@app.route("/stop", methods=["POST"])
def stop():
    with state_lock:
        if state.status == "running":
            state.stop_requested = True
            state.message = "Stop requested. Finishing current email before stopping."
    return jsonify({"ok": True})


@app.route("/download-log")
def download_log():
    log_path = request.args.get("path")
    if not log_path:
        return "Missing log path", 400
    safe_path = Path(log_path).resolve()
    if LOG_DIR not in safe_path.parents:
        return "Invalid path", 400
    if not safe_path.exists():
        return "Log not found", 404
    return send_file(safe_path, as_attachment=True)


@app.route("/start", methods=["POST"])
def start():
    global job_thread

    with state_lock:
        if state.status == "running":
            return jsonify({"ok": False, "error": "A send job is already running."}), 409

    form = request.form
    files = request.files

    from_email = form.get("from_email", "").strip()
    app_password = form.get("app_password", "").strip()
    from_name = form.get("from_name", "").strip()
    reply_to = form.get("reply_to", "").strip() or from_email

    subject_template = form.get("subject", "").strip()
    cover_letter = form.get("cover_letter", "").strip()
    signature = form.get("signature", "").strip()
    use_title = form.get("use_title") == "on"

    batch_size = int(form.get("batch_size", "50"))
    batch_delay_min = float(form.get("batch_delay", "5"))
    emails_per_min = int(form.get("emails_per_min", "20"))
    daily_cap = int(form.get("daily_cap", "1500"))

    excel_file = files.get("excel_file")
    resume_file = files.get("resume_file")

    if not from_email or not app_password:
        return jsonify({"ok": False, "error": "Gmail address and App Password are required."}), 400
    if not subject_template:
        return jsonify({"ok": False, "error": "Email subject is required."}), 400
    if not cover_letter:
        return jsonify({"ok": False, "error": "Cover letter text is required."}), 400
    if not excel_file or not resume_file:
        return jsonify({"ok": False, "error": "Excel file and resume attachment are required."}), 400

    excel_path = save_upload(excel_file)
    resume_path = save_upload(resume_file)

    try:
        recipients, skipped = load_recipients(excel_path)
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"ok": False, "error": f"Failed to read Excel: {exc}"}), 400

    if not recipients:
        return jsonify({"ok": False, "error": "No valid recipients found in the Excel file."}), 400

    config = {
        "from_email": from_email,
        "app_password": app_password,
        "from_name": from_name,
        "reply_to": reply_to,
        "subject_template": subject_template,
        "cover_letter": cover_letter,
        "signature": signature,
        "use_title": use_title,
        "batch_size": batch_size,
        "batch_delay_sec": int(batch_delay_min * 60),
        "emails_per_min": emails_per_min,
        "daily_cap": daily_cap,
        "resume_path": resume_path,
        "recipients": recipients,
        "skipped": skipped,
    }

    job_thread = threading.Thread(target=send_job, args=(config,), daemon=True)
    job_thread.start()

    return jsonify({"ok": True, "total": len(recipients), "skipped": len(skipped)})


def save_upload(storage) -> Path:
    filename = secure_filename(storage.filename or "upload")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = UPLOAD_DIR / f"{timestamp}_{filename}"
    storage.save(save_path)
    return save_path


def load_recipients(excel_path: Path) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    df = pd.read_excel(excel_path)
    normalized = {str(col).strip().lower(): col for col in df.columns}

    def col(name: str) -> str | None:
        return normalized.get(name.lower())

    name_col = col("name")
    email_col = col("email")
    title_col = col("title")
    company_col = col("company")

    if not name_col or not email_col or not company_col:
        raise ValueError("Excel must include Name, Email, and Company columns.")

    recipients: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []
    seen = set()

    def clean(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    for _, row in df.iterrows():
        name = clean(row.get(name_col, ""))
        email = clean(row.get(email_col, ""))
        title = clean(row.get(title_col, "")) if title_col else ""
        company = clean(row.get(company_col, ""))

        if not email or not EMAIL_RE.match(email):
            skipped.append(
                {
                    "name": name,
                    "email": email,
                    "title": title,
                    "company": company,
                    "reason": "invalid_email",
                }
            )
            continue

        key = email.lower()
        if key in seen:
            skipped.append(
                {
                    "name": name,
                    "email": email,
                    "title": title,
                    "company": company,
                    "reason": "duplicate_email",
                }
            )
            continue
        seen.add(key)

        recipients.append(
            {
                "name": name,
                "email": email,
                "title": title,
                "company": company,
            }
        )

    return recipients, skipped


def update_state(**kwargs) -> None:
    with state_lock:
        for key, value in kwargs.items():
            setattr(state, key, value)


def render_placeholders(text: str, context: Dict[str, str]) -> str:
    for key, value in context.items():
        text = text.replace("{" + key + "}", value)
    return text


def build_message(config: Dict[str, str], recipient: Dict[str, str]) -> EmailMessage:
    context = {
        "name": recipient.get("name") or "there",
        "email": recipient.get("email") or "",
        "title": recipient.get("title") or "",
        "company": recipient.get("company") or "",
    }

    name = context["name"].strip()
    title = context["title"].strip()
    if config["use_title"] and title:
        if name and name.lower() != "there":
            greeting = f"Hi {title} {name},"
        else:
            greeting = f"Hi {title},"
    else:
        greeting = f"Hi {name if name else 'there'},"

    cover_letter = render_placeholders(config["cover_letter"], context)
    signature = render_placeholders(config.get("signature", ""), context)

    body_parts = [greeting, "", cover_letter]
    if signature:
        body_parts.extend(["", signature])

    body = "\n".join(body_parts).strip() + "\n"

    subject = render_placeholders(config["subject_template"], context)

    msg = EmailMessage()
    msg["Subject"] = subject
    if config["from_name"]:
        msg["From"] = f"{config['from_name']} <{config['from_email']}>"
    else:
        msg["From"] = config["from_email"]
    msg["To"] = recipient["email"]
    msg["Reply-To"] = config["reply_to"]
    msg.set_content(body)

    attach_file(msg, config["resume_path"])
    return msg


def attach_file(msg: EmailMessage, path: Path) -> None:
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        maintype, subtype = mime_type.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"
    with open(path, "rb") as handle:
        msg.add_attachment(handle.read(), maintype=maintype, subtype=subtype, filename=path.name)


def send_job(config: Dict[str, str]) -> None:
    log_path = LOG_DIR / f"send_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    skipped_items = config.get("skipped", [])
    update_state(
        status="running",
        message=f"Starting send job. Skipping {len(skipped_items)} invalid/duplicate rows.",
        total=len(config["recipients"]),
        sent=0,
        failed=0,
        skipped=len(skipped_items),
        current="",
        started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        finished_at="",
        log_path=str(log_path),
        stop_requested=False,
    )

    emails_per_min = max(1, int(config["emails_per_min"]))
    per_email_delay = max(0, 60 / emails_per_min)
    batch_size = max(1, int(config["batch_size"]))
    batch_delay_sec = max(0, int(config["batch_delay_sec"]))
    daily_cap = max(1, int(config["daily_cap"]))

    sent_in_batch = 0
    sent_count = 0
    failed_count = 0

    with open(log_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["email", "name", "company", "status", "details"])
        for item in skipped_items:
            writer.writerow(
                [
                    item.get("email", ""),
                    item.get("name", ""),
                    item.get("company", ""),
                    "skipped",
                    item.get("reason", "skipped"),
                ]
            )

        try:
            smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config["from_email"], config["app_password"])
        except Exception as exc:  # pylint: disable=broad-except
            update_state(status="failed", message=f"SMTP login failed: {exc}")
            return

        try:
            for recipient in config["recipients"]:
                with state_lock:
                    if state.stop_requested:
                        update_state(status="stopped", message="Job stopped by user.")
                        break

                if sent_count >= daily_cap:
                    update_state(message="Daily cap reached. Stopping.")
                    break

                update_state(current=recipient["email"])

                try:
                    msg = build_message(config, recipient)
                    smtp.send_message(msg)
                    sent_count += 1
                    update_state(sent=sent_count, message="Sending...")
                    writer.writerow([recipient["email"], recipient.get("name", ""), recipient.get("company", ""), "sent", ""])
                except Exception as exc:  # pylint: disable=broad-except
                    failed_count += 1
                    update_state(failed=failed_count, message="Some emails failed. See log.")
                    writer.writerow([recipient["email"], recipient.get("name", ""), recipient.get("company", ""), "failed", str(exc)])

                sent_in_batch += 1
                time.sleep(per_email_delay)

                if sent_in_batch >= batch_size:
                    update_state(message=f"Batch sent. Waiting {batch_delay_sec} seconds...")
                    time.sleep(batch_delay_sec)
                    sent_in_batch = 0
        finally:
            smtp.quit()

    with state_lock:
        if state.status == "running":
            state.status = "completed"
            state.message = "Job completed."
        state.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.current = ""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, port=port)
