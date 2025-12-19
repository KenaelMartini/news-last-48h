# -*- coding: utf-8 -*-
"""
Nettoyage du report.md avant génération Word.
Supprime tous les caractères invisibles, symboles illégaux et retours chariot mal encodés.
"""

from pathlib import Path
import re

SRC = Path(r"D:\trading\News Last 48H\out\report.md")
DST = SRC.with_name("report_CLEAN.md")

print(f"🧹 Nettoyage du fichier source : {SRC}")

if not SRC.exists():
    print("❌ Fichier introuvable :", SRC)
    exit(1)

raw = SRC.read_text(encoding="utf-8", errors="ignore")

# Supprime caractères de contrôle interdits
clean = re.sub(r"[\x00-\x1F\x7F\u2028\u2029]", "", raw)

# Normalise les sauts de ligne
clean = clean.replace("\r\n", "\n").replace("\r", "\n")

# Supprime les triples lignes vides
clean = re.sub(r"\n{3,}", "\n\n", clean)

DST.write_text(clean, encoding="utf-8")

print(f"✅ report.md nettoyé → {DST}")
