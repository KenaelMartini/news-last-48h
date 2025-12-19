from models.idea import MacroIdea, MacroSessionReport
from datetime import date

def generate_example():
    idea = MacroIdea(
        asset="NZDUSD",
        direction="Short",
        conviction=0.75,
        drivers_core=[
            "China property drag weighs on NZ exports",
            "RBNZ constrained, low hawkish optionality",
            "Softening terms of trade"
        ],
        macro_context=[
            "US growth outperformance",
            "Commodity demand risk ex-energy"
        ],
        risk_to_view="China fiscal impulse surprises to upside",
        key_data_triggers=[
            "CN NBS PMI < 50",
            "US ISM > 52"
        ],
        sources=[
            "https://www.reuters.com",
            "https://rbnz.govt.nz"
        ],
        time_horizon="2-5 days",
        priority="High"
    )

    report = MacroSessionReport(
        date=str(date.today()),
        session="EU",
        macro_biases=[idea]
    )

    return report.model_dump()

if __name__ == "__main__":
    import json
    data = generate_example()
    with open("macro_ideas.json","w") as f:
        json.dump(data,f,indent=2)
    print("✅ JSON ready: macro_ideas.json")
