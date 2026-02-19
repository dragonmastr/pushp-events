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


configure_gtk_runtime()

from menu_generator import generate_menu_pdfs, reset_excel

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXCEL = BASE_DIR / "data" / "menu.xlsx"
DEFAULT_OUTPUT = None
TEMPLATE_EXCEL = None


def run_generation(path_var: tk.StringVar) -> None:
    excel_path = Path(path_var.get())
    if not excel_path.exists():
        messagebox.showerror("Missing File", "Please select a valid Excel file.")
        return

    try:
        output_en, output_hi = generate_menu_pdfs(excel_path)
    except Exception as exc:  # pylint: disable=broad-except
        messagebox.showerror("Generation Failed", f"Error: {exc}")
        return

    messagebox.showinfo(
        "Success",
        f"Menu PDFs created at:\n{output_en}\n{output_hi}",
    )


def run_reset(path_var: tk.StringVar) -> None:
    excel_path = Path(path_var.get())
    if not excel_path.exists():
        messagebox.showerror("Missing File", "Please select a valid Excel file.")
        return

    if not messagebox.askyesno("Reset Excel", "Create a fresh Excel file from the template?"):
        return
    save_path = filedialog.asksaveasfilename(
        title="Save Reset Excel As",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")],
        initialdir=str(excel_path.parent),
        initialfile=f"{excel_path.stem}.xlsx",
    )
    if not save_path:
        return

    try:
        reset_path = reset_excel(Path(save_path), TEMPLATE_EXCEL, create_new=False)
    except Exception as exc:  # pylint: disable=broad-except
        messagebox.showerror("Reset Failed", f"Error: {exc}")
        return

    path_var.set(str(reset_path))
    messagebox.showinfo("Reset Complete", f"Reset file created at:\\n{reset_path}")


def browse_excel(path_var: tk.StringVar) -> None:
    filepath = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files", "*.xlsx")],
        initialdir=str(DEFAULT_EXCEL.parent),
    )
    if filepath:
        path_var.set(filepath)


def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("Pushp Events - Menu Generator")
    root.geometry("520x220")
    root.resizable(False, False)

    path_var = tk.StringVar(value=str(DEFAULT_EXCEL))

    title = tk.Label(root, text="Menu Generator", font=("Arial", 16, "bold"))
    title.pack(pady=(16, 8))

    frame = tk.Frame(root)
    frame.pack(pady=6, padx=18, fill="x")

    path_entry = tk.Entry(frame, textvariable=path_var, width=48)
    path_entry.pack(side="left", fill="x", expand=True)

    browse_btn = tk.Button(frame, text="...", width=3, command=lambda: browse_excel(path_var))
    browse_btn.pack(side="left", padx=6)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=18)

    run_btn = tk.Button(btn_frame, text="Generate PDF", width=18, command=lambda: run_generation(path_var))
    run_btn.pack(side="left", padx=8)

    reset_btn = tk.Button(btn_frame, text="Reset Excel", width=18, command=lambda: run_reset(path_var))
    reset_btn.pack(side="left", padx=8)

    hint = tk.Label(
        root,
        text="Tip: Start and End dates in the Excel file auto-fill the meal counts sheet.",
        font=("Arial", 9),
        fg="#666666",
    )
    hint.pack(pady=(0, 10))

    return root


def main() -> None:
    root = build_ui()
    root.mainloop()


if __name__ == "__main__":
    main()
