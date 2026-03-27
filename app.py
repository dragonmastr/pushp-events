import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


def configure_gtk_runtime() -> None:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    gtk_bin = base_dir / "gtk" / "bin"
    if gtk_bin.exists():
        os.environ["PATH"] = str(gtk_bin) + os.pathsep + os.environ.get("PATH", "")
        return
    if os.name == "nt":
        system_gtk_bin = Path("C:/Program Files/GTK3-Runtime Win64/bin")
        if system_gtk_bin.exists():
            os.environ["PATH"] = str(system_gtk_bin) + os.pathsep + os.environ.get("PATH", "")


configure_gtk_runtime()

BASE_DIR    = Path(__file__).resolve().parent
DEFAULT_EXCEL = BASE_DIR / "data" / "menu.xlsx"
TEMPLATE_EXCEL = None

# ── Palette ────────────────────────────────────────────────────
BG        = "#F7F5F2"
HEADER_BG = "#2B1F1A"
CARD_BG   = "#FFFFFF"
BORDER    = "#E2DDD8"
MUTED     = "#A09488"
TEXT      = "#2C2420"
FG_LIGHT  = "#EDE8E3"

BTN_PRIMARY   = "#3D2B1F"
BTN_PRI_HVR   = "#5C4033"
BTN_SECONDARY = "#6B5248"
BTN_SEC_HVR   = "#856660"
BTN_GHOST     = "#FFFFFF"
BTN_GHOST_HVR = "#F2EDE8"
BTN_GHOST_BD  = "#C8BFB8"

STATUS_OK  = "#3A6B41"
STATUS_ERR = "#A63228"
STATUS_MID = "#6B5248"


# ── Custom button (Label-based — works on macOS Aqua) ──────────

class _Btn(tk.Frame):
    """Flat colored button that renders correctly on macOS."""

    def __init__(self, parent, text, command,
                 bg, fg, hover_bg,
                 font=("Helvetica Neue", 11),
                 pad_y=11, border_color=None, **kw):
        bd = 1 if border_color else 0
        super().__init__(parent, background=border_color or bg,
                         padx=bd, pady=bd, cursor="hand2", **kw)
        self._bg  = bg
        self._hbg = hover_bg
        self._cmd = command
        self._inner = tk.Frame(self, background=bg, cursor="hand2")
        self._inner.pack(fill="both", expand=True)
        self._lbl = tk.Label(
            self._inner, text=text,
            background=bg, foreground=fg,
            font=font, pady=pad_y, cursor="hand2",
        )
        self._lbl.pack(fill="both", expand=True)
        for w in (self, self._inner, self._lbl):
            w.bind("<Enter>",    self._on_enter)
            w.bind("<Leave>",    self._on_leave)
            w.bind("<Button-1>", self._on_click)

    def _on_enter(self, _=None):
        self._inner.configure(background=self._hbg)
        self._lbl.configure(background=self._hbg)

    def _on_leave(self, _=None):
        self._inner.configure(background=self._bg)
        self._lbl.configure(background=self._bg)

    def set_text(self, t):
        self._lbl.configure(text=t)

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        color = self._bg if enabled else "#A09488"
        self._lbl.configure(state=state, background=color)
        self._inner.configure(background=color)
        self.configure(background=color)

    def _on_click(self, _=None):
        if self._lbl.cget("state") != "disabled" and self._cmd:
            self._cmd()


# ── Logo loader ────────────────────────────────────────────────

def _load_logo(h=44):
    try:
        from PIL import Image, ImageTk
        for name in ("assets/logo.png", "assets/pushp-event-logo.png"):
            p = BASE_DIR / name
            if p.exists():
                img = Image.open(p).convert("RGBA")
                ratio = h / img.height
                img = img.resize((int(img.width * ratio), h), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
    except Exception:
        pass
    return None


# ── Generation callbacks ───────────────────────────────────────

def run_generation(path_var, btn, status_var):
    excel_path = Path(path_var.get())
    if not excel_path.exists():
        messagebox.showerror("Missing File", "Select a valid Excel file.")
        return
    output_dir = filedialog.askdirectory(
        title="Choose output folder",
        initialdir=str(Path.home() / "Documents"),
    )
    if not output_dir:
        return
    _busy(btn, "Generating…", status_var, "Generating menu PDFs — please wait")
    try:
        from menu_generator import generate_menu_pdfs
        en, hi = generate_menu_pdfs(excel_path, Path(output_dir))
    except Exception as exc:
        _idle(btn, "Generate Menu PDF")
        status_var.set(f"Error: {exc}")
        messagebox.showerror("Failed", str(exc))
        return
    _idle(btn, "Generate Menu PDF")
    status_var.set(f"Saved → {Path(en).name}  ·  {Path(hi).name}")
    messagebox.showinfo("Done", f"PDFs created:\n{en}\n{hi}")


def run_name_tags(path_var, btn, status_var):
    excel_path = Path(path_var.get())
    if not excel_path.exists():
        messagebox.showerror("Missing File", "Select a valid Excel file.")
        return
    save_path = filedialog.asksaveasfilename(
        title="Save Name Tags PDF",
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        initialdir=str(Path.home() / "Documents"),
        initialfile="name_tags.pdf",
    )
    if not save_path:
        return
    _busy(btn, "Generating…", status_var, "Building name tags — please wait")
    try:
        from menu_generator import generate_name_tags_pdf
        out = generate_name_tags_pdf(excel_path, Path(save_path))
    except Exception as exc:
        _idle(btn, "Generate Name Tags")
        status_var.set(f"Error: {exc}")
        messagebox.showerror("Failed", str(exc))
        return
    _idle(btn, "Generate Name Tags")
    status_var.set(f"Name tags saved → {Path(out).name}")
    messagebox.showinfo("Done", f"Name tags PDF:\n{out}")


def run_reset(path_var, status_var):
    excel_path = Path(path_var.get())
    if not messagebox.askyesno("Reset Excel", "Create a fresh Excel template?"):
        return
    initial_dir  = excel_path.parent if excel_path.exists() else Path.home() / "Documents"
    initial_name = f"{excel_path.stem}.xlsx" if excel_path.exists() else "menu.xlsx"
    save_path = filedialog.asksaveasfilename(
        title="Save Template As",
        defaultextension=".xlsx",
        filetypes=[("Excel", "*.xlsx")],
        initialdir=str(initial_dir),
        initialfile=initial_name,
    )
    if not save_path:
        return
    try:
        from menu_generator import reset_excel
        reset_path = reset_excel(Path(save_path), TEMPLATE_EXCEL, create_new=False)
    except Exception as exc:
        status_var.set(f"Error: {exc}")
        messagebox.showerror("Failed", str(exc))
        return
    path_var.set(str(reset_path))
    status_var.set(f"Template created → {Path(reset_path).name}")
    messagebox.showinfo("Done", f"Template saved:\n{reset_path}")


def browse_excel(path_var):
    f = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel", "*.xlsx")],
        initialdir=str(DEFAULT_EXCEL.parent),
    )
    if f:
        path_var.set(f)


def _busy(btn: _Btn, label: str, status_var, msg: str):
    btn.set_text(label)
    btn.set_enabled(False)
    status_var.set(msg)
    btn.update_idletasks()


def _idle(btn: _Btn, label: str):
    btn.set_text(label)
    btn.set_enabled(True)
    btn.update_idletasks()


# ── UI ─────────────────────────────────────────────────────────

def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("Pushp Events – Menu Generator")
    root.resizable(False, False)
    root.configure(background=BG)

    # ── Header ────────────────────────────────────────────────
    hdr = tk.Frame(root, background=HEADER_BG)
    hdr.pack(fill="x")

    hdr_inner = tk.Frame(hdr, background=HEADER_BG)
    hdr_inner.pack(padx=24, pady=14)

    logo = _load_logo(44)
    if logo:
        lbl = tk.Label(hdr_inner, image=logo, background=HEADER_BG)
        lbl.image = logo
        lbl.pack(side="left", padx=(0, 14))

    txt = tk.Frame(hdr_inner, background=HEADER_BG)
    txt.pack(side="left")
    tk.Label(txt, text="Pushp Events", font=("Georgia", 16, "bold"),
             background=HEADER_BG, foreground="#F0EAE4").pack(anchor="w")
    tk.Label(txt, text="Menu Generator", font=("Helvetica Neue", 10),
             background=HEADER_BG, foreground="#9C8880").pack(anchor="w")

    # ── Body ──────────────────────────────────────────────────
    body = tk.Frame(root, background=BG)
    body.pack(padx=20, pady=18, fill="x")

    # File picker
    tk.Label(body, text="Excel File", font=("Helvetica Neue", 9, "bold"),
             background=BG, foreground=MUTED).pack(anchor="w", pady=(0, 5))

    path_var = tk.StringVar(value=str(DEFAULT_EXCEL))

    row = tk.Frame(body, background=BG)
    row.pack(fill="x")

    # Entry with 1-px border frame
    ef = tk.Frame(row, background=BORDER, padx=1, pady=1)
    ef.pack(side="left", fill="x", expand=True)
    entry = tk.Entry(ef, textvariable=path_var, relief="flat",
                     background=CARD_BG, foreground=TEXT,
                     font=("Helvetica Neue", 10), insertbackground=BTN_PRIMARY)
    entry.pack(fill="x", expand=True, ipady=6, ipadx=6)

    browse = _Btn(row, "Browse", lambda: browse_excel(path_var),
                  bg=BTN_GHOST, fg=TEXT, hover_bg=BTN_GHOST_HVR,
                  font=("Helvetica Neue", 10), pad_y=7,
                  border_color=BTN_GHOST_BD)
    browse.pack(side="left", padx=(7, 0))

    # Separator
    tk.Frame(body, background=BORDER, height=1).pack(fill="x", pady=16)

    # Primary buttons
    status_var = tk.StringVar(value="Ready")

    gen_btn = _Btn(body, "Generate Menu PDF", None,
                   bg=BTN_PRIMARY, fg="#F0EAE4", hover_bg=BTN_PRI_HVR,
                   font=("Helvetica Neue", 11, "bold"), pad_y=12)
    gen_btn._cmd = lambda: run_generation(path_var, gen_btn, status_var)
    gen_btn.pack(fill="x", pady=(0, 7))

    tag_btn = _Btn(body, "Generate Name Tags", None,
                   bg=BTN_SECONDARY, fg="#F0EAE4", hover_bg=BTN_SEC_HVR,
                   font=("Helvetica Neue", 11), pad_y=12)
    tag_btn._cmd = lambda: run_name_tags(path_var, tag_btn, status_var)
    tag_btn.pack(fill="x", pady=(0, 0))

    # Separator
    tk.Frame(body, background=BORDER, height=1).pack(fill="x", pady=16)

    # Ghost / outline reset button
    reset = _Btn(body, "Reset / New Excel Template", lambda: run_reset(path_var, status_var),
                 bg=BTN_GHOST, fg=MUTED, hover_bg=BTN_GHOST_HVR,
                 font=("Helvetica Neue", 10), pad_y=9,
                 border_color=BTN_GHOST_BD)
    reset.pack(fill="x")

    # ── Status bar ────────────────────────────────────────────
    tk.Frame(root, background=BORDER, height=1).pack(fill="x", pady=(6, 0))

    sb = tk.Frame(root, background=BG)
    sb.pack(fill="x")

    dot = tk.Label(sb, text="●", font=("Helvetica Neue", 8),
                   background=BG, foreground=MUTED)
    dot.pack(side="left", padx=(14, 4), pady=7)

    slbl = tk.Label(sb, textvariable=status_var, font=("Helvetica Neue", 9),
                    background=BG, foreground=MUTED, anchor="w")
    slbl.pack(side="left", pady=7)

    def _track(*_):
        t = status_var.get().lower()
        if any(k in t for k in ("error", "failed")):
            c = STATUS_ERR
        elif any(k in t for k in ("saved", "created", "complete")):
            c = STATUS_OK
        elif any(k in t for k in ("wait", "generating", "building")):
            c = STATUS_MID
        else:
            c = MUTED
        dot.configure(foreground=c)
        slbl.configure(foreground=c)

    status_var.trace_add("write", _track)

    root.update_idletasks()
    root.geometry("")
    root.update_idletasks()
    root.minsize(root.winfo_width(), root.winfo_height())

    return root


def main():
    root = build_ui()
    root.mainloop()


if __name__ == "__main__":
    main()
