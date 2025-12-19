from pathlib import Path
from datetime import datetime
import subprocess
from datetime import datetime, timezone


BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "KMCO_out"
OUT.mkdir(exist_ok=True)

HOURS = 12  # fenêtre overnight
NOW = datetime.now(timezone.utc).strftime("%d %B %Y")

# 1. Collecte des flux
subprocess.run([
    "python", str(BASE / "src" / "news48_dump.py"),
    "--outdir", str(OUT),
    "--hours", str(HOURS)
])


# 2. Génération du markdown court
md_path = OUT / "report_overnight.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write(f"# KM&CO Overnight Macro Check – {NOW}\n\n")
    f.write("## 1. Top Overnight Drivers\n")
    f.write("_Résumé automatique à insérer ici._\n\n")
    f.write("## 2. Marchés & Devises\n_Résumé en texte..._\n\n")

# 3. Génération du Word avec en-tête institutionnelle
subprocess.run([
    "python", str(BASE / "src" / "generate_desk_report.py"),
    "--md", str(md_path)
])
