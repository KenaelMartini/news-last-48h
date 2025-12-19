from models.idea import MacroIdea, MacroSessionReport
import pandas as pd
from kmco_save import save_json, save_table, save_log

# Build idea example
idea = MacroIdea(
    asset="NZDUSD",
    direction="Short",
    conviction=0.75,
    drivers_core=[
        "China property drag weighs on NZ exports",
        "RBNZ capped, limited optionality",
        "Softening terms of trade"
    ],
    macro_context=["US outperformance","Commodity softness"],
    risk_to_view="China stimulus surprise",
    key_data_triggers=["CN PMI < 50", "US ISM > 52"],
    sources=["https://www.reuters.com"],
    time_horizon="2-5 days",
    priority="High"
)

# Build the JSON structure
report = MacroSessionReport(
    date="2025-11-03",
    session="EU",
    macro_biases=[idea]
)

# Build the DataFrame
rows = [{
    "Asset": idea.asset,
    "Direction": idea.direction,
    "Conviction": idea.conviction,
    "Drivers": " | ".join(idea.drivers_core),
    "Triggers": " | ".join(idea.key_data_triggers),
    "Risk": idea.risk_to_view,
    "Sources": " | ".join(idea.sources)
}]
df = pd.DataFrame(rows)

# Save both
json_data = report.model_dump()
save_json(json_data, session="EU")
save_table(df, session="EU")
save_log("Generated EU macro ideas & table successfully.")

print("✅ Done.")
