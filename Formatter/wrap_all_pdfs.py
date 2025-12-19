# wrap_all_pdfs.py
import os
import re
from datetime import datetime
from format_pdf_wrapper import format_pdf_to_kmco


BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, "Input")
OUTPUT = os.path.join(BASE, "Output")

os.makedirs(INPUT, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)


def sanitize_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = name.replace("/", "_").replace("\\", "_")
    name = name.replace(":", "_")
    name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
    return name


print("[KM&CO] PDF Wrapper lancé...")
print(f"[KM&CO] Input : {INPUT}")
print(f"[KM&CO] Output : {OUTPUT}")

for file in os.listdir(INPUT):
    if not file.lower().endswith(".pdf"):
        continue

    input_path = os.path.join(INPUT, file)
    base_name = os.path.splitext(file)[0] + "_KMCO.pdf"
    output_filename = sanitize_filename(base_name)
    output_path = os.path.join(OUTPUT, output_filename)

    print(f"[KM&CO] → Encapsulation : {file}")
    format_pdf_to_kmco(input_path, output_path, date=datetime.now())

print("[KM&CO] Terminé.")
