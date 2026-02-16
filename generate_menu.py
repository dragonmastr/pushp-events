from pathlib import Path
import sys

from menu_generator import generate_menu_pdfs

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    excel_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "data" / "menu.xlsx"
    output_en, output_hi = generate_menu_pdfs(excel_path)
    print(f\"\u2705 Menu PDFs generated successfully:\\n- {output_en}\\n- {output_hi}\")


if __name__ == "__main__":
    main()
