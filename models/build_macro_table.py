import os, json
import pandas as pd
from datetime import datetime

# Chemin racine de ton pipeline
BASE_PATH = r"D:\trading\News Last 48H\kmco_pipeline"

# Session à remplacer plus tard par un argument CLI (EU, US, ASIA...)
session = "EU"

# Génère la date du jour au format YYYY-MM-DD
date_str = datetime.now().strftime("%Y-%m-%d")

# Chemin dynamique vers ton fichier JSON d'idées macro
json_path = os.path.join(
    BASE_PATH,
    "data",
    "ideas",
    f"macro_ideas_{date_str}_{session}.json"
)

# Lecture du JSON
with open(json_path, "r") as f:
    data = json.load(f)

# Construction du tableau
rows = []
for idea in data["macro_biases"]:
    rows.append({
        "Asset": idea["asset"],
        "Direction": idea["direction"],
        "Conviction": idea["conviction"],
        "Drivers": " | ".join(idea["drivers_core"]),
        "Key Triggers": " | ".join(idea["key_data_triggers"]),
        "Risk": idea["risk_to_view"],
        "Sources": " | ".join(idea["sources"])
    })

df = pd.DataFrame(rows)

# Sauvegarde CSV / Excel
tables_dir = os.path.join(BASE_PATH, "data", "tables")
os.makedirs(tables_dir, exist_ok=True)

excel_path = os.path.join(tables_dir, f"macro_table_{date_str}_{session}.xlsx")
csv_path   = os.path.join(tables_dir, f"macro_table_{date_str}_{session}.csv")

df.to_excel(excel_path, index=False)
df.to_csv(csv_path, index=False)

print(f"✅ Table saved to:\n{excel_path}\n{csv_path}")
