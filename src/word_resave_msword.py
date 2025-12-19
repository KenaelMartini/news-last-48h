import win32com.client
from pathlib import Path

src = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24_FULLFIX.docx")
dst = src.with_name(src.stem + "_MSWORD.docx")

word = win32com.client.Dispatch("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
doc = word.Documents.Open(str(src))
doc.SaveAs2(str(dst), FileFormat=16)  # 16 = DOCX natif Word
doc.Close()
word.Quit()

print("✅ Fichier recréé par Word :", dst)
