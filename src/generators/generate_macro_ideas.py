import sys, os, json
from datetime import datetime

# --- FIX POUR IMPORTER MODELS PEU IMPORTE OU TU LANCES LE SCRIPT ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)
# -------------------------------------------------------------------

from models.idea import MacroIdea, MacroSessionReport


INPUT_FILE = r"D:\trading\News Last 48H\KMCO_out\articles.json"

def load_articles():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw["articles"] if "articles" in raw else raw

def create_placeholder_idea():
    return MacroIdea(
        asset="EURUSD",
        direction="Long",
        conviction=0.50,
        drivers_core=["Placeholder driver: données économiques européennes résilientes"],
        macro_context=["Appétit pour le risque modéré, USD moins demandé"],
        risk_to_view="Choc risk-off global",
        key_data_triggers=["ISM US", "PMI Europe"],
        sources=["https://www.reuters.com"],
        time_horizon="2-5 jours",
        priority="Medium"
    )

if __name__ == "__main__":
    articles = load_articles()

    idea = create_placeholder_idea()

    report = MacroSessionReport(
        date=datetime.now().strftime("%Y-%m-%d"),
        session="EU",
        macro_biases=[idea]
    )

    print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    print("\n✅ Macro ideas JSON généré.")
