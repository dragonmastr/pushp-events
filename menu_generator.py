from __future__ import annotations

from collections import defaultdict
import sys
from datetime import datetime, date
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Tuple

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from openpyxl import load_workbook

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

MEAL_ORDER = ["Breakfast", "Lunch", "Hi-tea", "Dinner"]

MEAL_LABELS_EN = {
    "Breakfast": "Breakfast",
    "Lunch": "Lunch",
    "Hi-tea": "Hi-tea",
    "Dinner": "Dinner",
}

MEAL_LABELS_HI = {
    "Breakfast": "नाश्ता",
    "Lunch": "दोपहर का भोजन",
    "Hi-tea": "हाई टी",
    "Dinner": "रात्रि भोजन",
}

CATEGORY_LABELS_HI = {
    "live": "लाइव",
    "starter": "स्टार्टर",
    "main course": "मुख्य व्यंजन",
    "maincourse": "मुख्य व्यंजन",
    "bread": "ब्रेड",
    "raita": "रायता",
    "sides": "साइड्स",
    "salad": "सलाद",
    "condiments": "मसाले",
    "counter": "काउंटर",
    "snacks": "स्नैक्स",
    "beverages": "पेय",
    "dessert": "मिठाई",
    "static": "स्टैटिक",
    "live counter": "लाइव काउंटर",
    "soup": "सूप",
}

LABELS_EN = {
    "client_name": "Client Name",
    "venue": "Venue",
    "total_pax": "Total Pax",
    "start_date": "Start Date",
    "end_date": "End Date",
    "caterer": "Caterer",
    "phone": "Phone",
    "dinner_planner": "Dinner Planner",
    "count": "Count",
    "generated_on": "Generated on",
    "brand": "Pushp Events",
}

LABELS_HI = {
    "client_name": "क्लाइंट नाम",
    "venue": "स्थान",
    "total_pax": "कुल पैक्स",
    "start_date": "प्रारंभ तिथि",
    "end_date": "समाप्ति तिथि",
    "caterer": "कैटरर",
    "phone": "फोन",
    "dinner_planner": "डिनर प्लानर",
    "count": "गणना",
    "generated_on": "तैयार",
    "brand": "Pushp Events",
}

MONTHS_HI = {
    1: "जनवरी",
    2: "फरवरी",
    3: "मार्च",
    4: "अप्रैल",
    5: "मई",
    6: "जून",
    7: "जुलाई",
    8: "अगस्त",
    9: "सितंबर",
    10: "अक्टूबर",
    11: "नवंबर",
    12: "दिसंबर",
}


# ---------------- HELPERS ----------------

def clean(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def normalize_key(key: str) -> str:
    key = clean(key).lower()
    key = key.replace("&", "and")
    key = key.replace("-", " ").replace("_", " ")
    key = " ".join(key.split())
    return key


EVENT_KEY_ALIASES = {
    "event_name": ["event name", "event", "event title"],
    "event_name_hi": ["event name hi", "event_name_hi", "event title hi", "event name hindi"],
    "client_name": ["client name", "client", "client_name"],
    "client_name_hi": ["client name hi", "client_name_hi", "client name hindi"],
    "venue": ["venue", "event venue", "location"],
    "venue_hi": ["venue hi", "venue_hindi", "venue_hi", "location hi"],
    "start_date": ["start date", "start", "start date (dd/mm/yyyy)"],
    "end_date": ["end date", "end", "end date (dd/mm/yyyy)"],
    "total_pax": ["total pax", "pax", "total pax size", "total guests"],
    "caterer_name": ["caterer name", "cater's name", "cater name", "caterer"],
    "caterer_phone": [
        "caterer phone",
        "caterer number",
        "cater's number",
        "phone",
        "contact phone",
        "contact_phone",
    ],
    "logo_path": ["logo", "logo path", "logo file", "caterer logo", "cater's logo"],
    "planner_name": ["planner name", "event planner", "dinner planner name", "planner"],
    "planner_name_hi": ["planner name hi", "planner_name_hi", "planner name hindi"],
    "caterer_name_hi": ["caterer name hi", "caterer_name_hi", "caterer name hindi"],
}


def normalize_event_info(raw: Dict[str, object]) -> Dict[str, object]:
    normalized = {}
    reverse_lookup = {}

    for canonical, aliases in EVENT_KEY_ALIASES.items():
        for alias in aliases:
            reverse_lookup[normalize_key(alias)] = canonical

    for key, value in raw.items():
        canonical = reverse_lookup.get(normalize_key(key), normalize_key(key))
        normalized[canonical] = value

    return normalized


def parse_date(value: object) -> Optional[date]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def format_date(value: Optional[date]) -> str:
    if not value:
        return ""
    return value.strftime("%d %B %Y")


def format_date_localized(value: Optional[date], lang: str) -> str:
    if not value:
        return ""
    if lang == "hi":
        month = MONTHS_HI.get(value.month, value.strftime("%B"))
        return f"{value.day:02d} {month} {value.year}"
    return value.strftime("%d %B %Y")


def normalize_meal(meal: str) -> str:
    raw = normalize_key(meal)
    if not raw:
        return ""
    if raw in {"breakfast", "bf"}:
        return "Breakfast"
    if raw in {"lunch"}:
        return "Lunch"
    if raw in {"hi tea", "hi-tea", "hitea", "high tea", "high-tea"}:
        return "Hi-tea"
    if raw in {"dinner"}:
        return "Dinner"
    return clean(meal)


# ---------------- EXCEL IO ----------------

def read_event_info(xlsx_path: Path) -> Dict[str, object]:
    df = pd.read_excel(xlsx_path, sheet_name="event_info")
    if "key" in df.columns and "value" in df.columns:
        raw = {
            clean(k): v
            for k, v in zip(df["key"], df["value"])
            if clean(k)
        }
    else:
        row = df.iloc[0].to_dict() if len(df) else {}
        raw = {clean(k): v for k, v in row.items() if clean(k)}
    return normalize_event_info(raw)


def read_menu_data(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name="menu")
    return df


def get_date_range(
    event_info: Dict[str, object], menu_dates: List[date]
) -> Tuple[Optional[date], Optional[date]]:
    start_date = parse_date(event_info.get("start_date"))
    end_date = parse_date(event_info.get("end_date"))

    if not start_date or not end_date:
        if menu_dates:
            start_date = min(menu_dates)
            end_date = max(menu_dates)

    return start_date, end_date


def ensure_template_exists(template_path: Path, source_excel: Path) -> None:
    if template_path.exists():
        return
    template_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_excel, template_path)


def ensure_meal_counts_sheet(
    xlsx_path: Path,
    date_list: List[date],
    default_pax: object,
    meal_order: List[str] = MEAL_ORDER,
) -> None:
    wb = load_workbook(xlsx_path)
    if "meal_counts" in wb.sheetnames:
        wb.close()
        return

    ws = wb.create_sheet("meal_counts")
    ws.append(["date", "meal", "count"])

    # Create formula-driven rows so Excel can auto-generate dates and meals
    formula_total = (
        '(INDEX(event_info!B:B, MATCH("end_date", event_info!A:A, 0)) - '
        'INDEX(event_info!B:B, MATCH("start_date", event_info!A:A, 0)) + 1) * 4'
    )
    formula_date = (
        '=IFERROR(IF(ROW()-1 <= {total}, '
        'INDEX(event_info!B:B, MATCH("start_date", event_info!A:A, 0)) + INT((ROW()-2)/4), ""), "")'
    ).format(total=formula_total)
    formula_meal = (
        '=IFERROR(IF(ROW()-1 <= {total}, '
        'CHOOSE(MOD(ROW()-2,4)+1, "Breakfast", "Lunch", "Hi-tea", "Dinner"), ""), "")'
    ).format(total=formula_total)
    formula_count = (
        '=IFERROR(IF(ROW()-1 <= {total}, '
        'INDEX(event_info!B:B, MATCH("total_pax", event_info!A:A, 0)), ""), "")'
    ).format(total=formula_total)

    # Pre-fill enough rows for long events
    for _ in range(2, 1502):
        ws.append([None, None, None])

    for row_idx in range(2, 1502):
        ws[f"A{row_idx}"].value = formula_date
        ws[f"B{row_idx}"].value = formula_meal
        ws[f"C{row_idx}"].value = formula_count

    wb.save(xlsx_path)
    wb.close()


def read_meal_counts(
    xlsx_path: Path,
    default_count: Optional[object] = None,
) -> Dict[date, Dict[str, object]]:
    try:
        wb = load_workbook(xlsx_path, data_only=True)
    except Exception:
        return {}

    if "meal_counts" not in wb.sheetnames:
        wb.close()
        return {}

    ws = wb["meal_counts"]
    headers = {}
    for idx, cell in enumerate(next(ws.iter_rows(min_row=1, max_row=1)), start=1):
        key = normalize_key(cell.value)
        if key:
            headers[key] = idx

    date_idx = headers.get("date", 1)
    meal_idx = headers.get("meal", 2)
    count_idx = headers.get("count") or headers.get("pax") or 3

    meal_counts: Dict[date, Dict[str, object]] = defaultdict(dict)
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = parse_date(row[date_idx - 1] if len(row) >= date_idx else None)
        meal = normalize_meal(row[meal_idx - 1] if len(row) >= meal_idx else "")
        count_val = row[count_idx - 1] if len(row) >= count_idx else None
        if count_val in (None, "") and default_count not in (None, ""):
            count_val = default_count
        if not d or not meal:
            continue
        meal_counts[d][meal] = count_val

    wb.close()
    return meal_counts


def parse_count(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def compute_date_counts(
    meal_counts: Dict[date, Dict[str, object]]
) -> Dict[date, Optional[float]]:
    date_counts: Dict[date, Optional[float]] = {}
    for d, meals in meal_counts.items():
        values = [parse_count(v) for v in meals.values()]
        values = [v for v in values if v is not None]
        if values:
            date_counts[d] = sum(values)
        else:
            date_counts[d] = None
    return date_counts


# ---------------- MENU BUILD ----------------

def build_menu_tree(menu_df: pd.DataFrame) -> Dict[date, Dict[str, Dict[str, List[str]]]]:
    menu_tree: Dict[date, Dict[str, Dict[str, List[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for _, row in menu_df.iterrows():
        row_date = parse_date(row.get("date"))
        meal = normalize_meal(row.get("meal", ""))
        category = clean(row.get("category", ""))
        item = clean(row.get("item", ""))

        if not row_date or not meal or not item:
            continue

        if not category:
            category = "Menu"

        menu_tree[row_date][meal][category].append(item)

    return menu_tree


def build_date_pages(
    date_list: List[date],
    menu_tree: Dict[date, Dict[str, Dict[str, List[str]]]],
    meal_counts: Dict[date, Dict[str, object]],
    date_counts: Dict[date, Optional[float]],
    meal_label_map: Dict[str, str],
    date_formatter,
    meal_order: List[str] = MEAL_ORDER,
) -> List[Dict[str, object]]:
    pages: List[Dict[str, object]] = []

    for d in date_list:
        meals = []
        for meal in meal_order:
            categories = menu_tree.get(d, {}).get(meal, {})
            pax = meal_counts.get(d, {}).get(meal, "")
            if categories or pax or meal in menu_tree.get(d, {}):
                meals.append(
                    {
                        "name": meal,
                        "display_name": meal_label_map.get(meal, meal),
                        "pax": clean(pax),
                        "categories": categories,
                    }
                )

        # append any custom meals not in MEAL_ORDER
        for meal, categories in menu_tree.get(d, {}).items():
            if meal not in meal_order:
                pax = meal_counts.get(d, {}).get(meal, "")
                meals.append(
                    {
                        "name": meal,
                        "display_name": meal_label_map.get(meal, meal),
                        "pax": clean(pax),
                        "categories": categories,
                    }
                )

        left_meals: List[Dict[str, object]] = []
        right_meals: List[Dict[str, object]] = []
        for meal in meals:
            name = meal.get("name", "")
            if name in {"Breakfast", "Hi-tea"}:
                left_meals.append(meal)
            elif name in {"Lunch", "Dinner"}:
                right_meals.append(meal)
            else:
                if len(left_meals) <= len(right_meals):
                    left_meals.append(meal)
                else:
                    right_meals.append(meal)

        pages.append(
            {
                "date": date_formatter(d),
                "count": "" if date_counts.get(d) is None else int(date_counts[d]),
                "meals": meals,
                "left_meals": left_meals,
                "right_meals": right_meals,
            }
        )

    return pages


# ---------------- PDF GENERATION ----------------

def generate_menu_pdf(
    excel_path: Path,
    output_path: Optional[Path] = None,
    template_path: Optional[Path] = None,
    labels: Optional[Dict[str, str]] = None,
    meal_label_map: Optional[Dict[str, str]] = None,
    event_name_override: Optional[str] = None,
    category_labels: Optional[Dict[str, str]] = None,
    lang: str = "en",
) -> Path:
    excel_path = Path(excel_path)
    if output_path is None:
        output_path = excel_path.parent / "output" / "Pushp_Events_Menu.pdf"
    output_path = Path(output_path)

    if template_path is None:
        template_path = BASE_DIR / "data" / "menu_template.xlsx"

    event_info = read_event_info(excel_path)

    menu_df = read_menu_data(excel_path)
    menu_tree = build_menu_tree(menu_df)

    menu_dates = sorted(menu_tree.keys())
    start_date, end_date = get_date_range(event_info, menu_dates)

    if start_date and end_date:
        date_list = [d.date() for d in pd.date_range(start_date, end_date, freq="D")]
    else:
        date_list = menu_dates

    default_pax = event_info.get("total_pax", "")
    if isinstance(default_pax, float) and pd.isna(default_pax):
        default_pax = ""

    if date_list:
        ensure_meal_counts_sheet(excel_path, date_list, default_pax)

    meal_counts = read_meal_counts(excel_path, default_pax)
    date_counts = compute_date_counts(meal_counts)

    if labels is None:
        labels = LABELS_EN
    if meal_label_map is None:
        meal_label_map = MEAL_LABELS_EN
    if category_labels is None:
        category_labels = {}

    date_formatter = lambda d: format_date_localized(d, lang)

    date_pages = build_date_pages(
        date_list, menu_tree, meal_counts, date_counts, meal_label_map, date_formatter
    )

    logo_path = clean(event_info.get("logo_path")) or "assets/logo.png"
    font_path = "assets/NotoSerifDevanagari-Regular.ttf"

    total_pax_value = clean(event_info.get("total_pax"))
    if not total_pax_value:
        numeric_counts = [v for v in date_counts.values() if v is not None]
        if numeric_counts:
            total_pax_value = str(int(max(numeric_counts)))

    def localized_value(key: str) -> str:
        if lang == "hi":
            hi_key = f"{key}_hi"
            hi_val = clean(event_info.get(hi_key))
            if hi_val:
                return hi_val
        return clean(event_info.get(key))

    event_name_value = localized_value("event_name")
    if event_name_override:
        event_name_value = event_name_override

    event = {
        "event_name": event_name_value,
        "event_name_hi": clean(event_info.get("event_name_hi")),
        "client_name": localized_value("client_name"),
        "venue": localized_value("venue"),
        "start_date": format_date_localized(start_date, lang),
        "end_date": format_date_localized(end_date, lang),
        "total_pax": total_pax_value,
        "caterer_name": localized_value("caterer_name"),
        "caterer_phone": clean(event_info.get("caterer_phone")),
        "planner_name": localized_value("planner_name"),
        "logo_path": logo_path,
    }

    env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))
    template = env.get_template("menu.html")

    html_out = template.render(
        event=event,
        date_pages=date_pages,
        logo_path=logo_path,
        font_path=font_path,
        generated_on=format_date_localized(datetime.now().date(), lang),
        labels=labels,
        category_labels=category_labels,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=html_out, base_url=str(BASE_DIR)).write_pdf(str(output_path))

    ensure_template_exists(Path(template_path), excel_path)

    return output_path


def safe_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else " " for ch in name)
    cleaned = "_".join(cleaned.split())
    return cleaned or "Menu"


def generate_menu_pdfs(excel_path: Path) -> Tuple[Path, Path]:
    excel_path = Path(excel_path)
    event_info = read_event_info(excel_path)
    event_name = clean(event_info.get("event_name")) or "Menu"
    event_name_hi = clean(event_info.get("event_name_hi")) or event_name

    output_dir = excel_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    base_en = safe_filename(event_name)
    base_hi = safe_filename(event_name_hi)

    output_en = output_dir / f"{base_en}_English.pdf"
    output_hi = output_dir / f"{base_hi}_Hindi.pdf"

    generate_menu_pdf(
        excel_path,
        output_path=output_en,
        labels=LABELS_EN,
        meal_label_map=MEAL_LABELS_EN,
        event_name_override=event_name,
        category_labels={},
        lang="en",
    )
    generate_menu_pdf(
        excel_path,
        output_path=output_hi,
        labels=LABELS_HI,
        meal_label_map=MEAL_LABELS_HI,
        event_name_override=event_name_hi,
        category_labels=CATEGORY_LABELS_HI,
        lang="hi",
    )

    return output_en, output_hi


# ---------------- RESET ----------------

def reset_excel(
    excel_path: Path,
    template_path: Optional[Path] = None,
    create_new: bool = True,
) -> Path:
    excel_path = Path(excel_path)
    if template_path is None:
        template_path = BASE_DIR / "data" / "menu_template.xlsx"

    template_path = Path(template_path)
    if not template_path.exists():
        template_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(excel_path, template_path)

    if create_new:
        reset_path = excel_path.parent / f"{excel_path.stem}_reset.xlsx"
        shutil.copy2(template_path, reset_path)
        return reset_path

    shutil.copy2(template_path, excel_path)
    return excel_path
