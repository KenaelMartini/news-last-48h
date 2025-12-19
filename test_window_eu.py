from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

ARTICLES = Path("D:/trading/News Last 48H/KMCO_out/articles.json")

with open(ARTICLES, "r", encoding="utf-8") as f:
    data = json.load(f)

now = datetime.now(timezone.utc)

# Fenêtre Europe stricte : 06h → 14h UTC
start_eu = now.replace(hour=6, minute=0, second=0, microsecond=0)
end_eu = now.replace(hour=14, minute=0, second=0, microsecond=0)

count_in = 0
count_out = 0

for a in data.get("articles", []):
    try:
        ts = datetime.fromisoformat(a["published_utc"].replace("Z", "+00:00"))
        if start_eu <= ts <= end_eu:
            count_in += 1
        else:
            count_out += 1
    except Exception:
        count_out += 1

print("now UTC:", now)
print("start_eu:", start_eu)
print("end_eu:", end_eu)

for a in data["articles"]:
    ts = datetime.fromisoformat(a["published_utc"].replace("Z", "+00:00"))
    if start_eu <= ts <= end_eu:
        print("✅ IN:", a["published_utc"], a["title"])
    else:
        print("❌ OUT:", a["published_utc"], a["title"])

