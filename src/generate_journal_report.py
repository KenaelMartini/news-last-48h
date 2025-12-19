import argparse
from datetime import datetime
import pdfplumber
from Formatter.ai_formatter_journal import format_journal

def extract_text_from_pdf(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    raw_text = extract_text_from_pdf(args.input)

    output = args.output or args.input.replace(".pdf", "_KMCO.docx")
    format_journal(raw_text, output_path=output, date=datetime.now())

    print(f"[KM&CO] Rapport généré : {output}")
