import zipfile, tempfile, shutil
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree

src = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24.docx")
dst = src.with_name(src.stem + "_FULLFIX.docx")

print("🔧 Reconstruction OPC complète…")

tmpdir = Path(tempfile.mkdtemp())
with zipfile.ZipFile(src, "r") as zin:
    zin.extractall(tmpdir)

# --- Reconstruction propre des relations document.xml.rels ---
rels_path = tmpdir / "word" / "_rels" / "document.xml.rels"
root = Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
SubElement(root, "Relationship", Id="rId1",
           Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
           Target="styles.xml")
SubElement(root, "Relationship", Id="rId2",
           Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings",
           Target="settings.xml")
SubElement(root, "Relationship", Id="rId3",
           Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/webSettings",
           Target="webSettings.xml")
SubElement(root, "Relationship", Id="rId4",
           Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
           Target="theme/theme1.xml")
ElementTree(root).write(rels_path, encoding="utf-8", xml_declaration=True)

# --- Reconstruction propre du [Content_Types].xml ---
ct = Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
defaults = [
    ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
    ("xml", "application/xml")
]
for ext, ctype in defaults:
    d = SubElement(ct, "Default"); d.set("Extension", ext); d.set("ContentType", ctype)

overrides = [
    ("/word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
    ("/word/styles.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"),
    ("/word/settings.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"),
    ("/word/webSettings.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"),
    ("/word/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml")
]
for part, ctype in overrides:
    o = SubElement(ct, "Override"); o.set("PartName", part); o.set("ContentType", ctype)

ElementTree(ct).write(tmpdir / "[Content_Types].xml", encoding="utf-8", xml_declaration=True)

# --- Recompression finale ---
with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for file in sorted(tmpdir.rglob("*")):
        if file.is_file():
            zout.write(file, file.relative_to(tmpdir))

shutil.rmtree(tmpdir)
print(f"✅ DOCX reconstruit : {dst}")
