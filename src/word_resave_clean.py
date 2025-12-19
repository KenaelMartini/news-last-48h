import win32com.client, os, sys
from pathlib import Path

src = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24.docx")
dst = src.with_name(src.stem + "_WORDCLEAN.docx")

print("🧽 Word purification en cours…")

word = win32com.client.Dispatch("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

doc = word.Documents.Open(str(src))
doc.SaveAs2(str(dst), FileFormat=16)  # 16 = DOCX natif
doc.Close()
word.Quit()

print("✅ Fichier nettoyé par Word :", dst)
