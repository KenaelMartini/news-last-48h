from pathlib import Path
from docx import Document

md_path = Path(r"D:\trading\News Last 48H\out\report.md")
out_path = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_CLEAN_SIMPLE.docx")

text = md_path.read_text(encoding="utf-8", errors="ignore")

doc = Document()
doc.add_heading("Analyse Globale du Marché", level=1)
for paragraph in text.split("\n\n"):
    p = paragraph.strip()
    if p:
        doc.add_paragraph(p)

out_path.parent.mkdir(parents=True, exist_ok=True)
doc.save(out_path)
print(f"✅ Fichier Word de base généré : {out_path}")
