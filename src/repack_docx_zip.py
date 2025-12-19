import zipfile, shutil, tempfile
from pathlib import Path

src = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24.docx")
dst = src.with_name(src.stem + "_REPACKED.docx")

print(f"🔧 Recompression OPC propre : {src.name}")

# décompression dans un dossier temporaire
tmpdir = Path(tempfile.mkdtemp())
with zipfile.ZipFile(src, "r") as zin:
    zin.extractall(tmpdir)

# recompression propre
with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for file in sorted(tmpdir.rglob("*")):
        if file.is_file():
            zout.write(file, file.relative_to(tmpdir))

shutil.rmtree(tmpdir)
print(f"✅ Fichier recompressé : {dst}")
