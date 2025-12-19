# ai_core/intelligence/data_extraction.py
import re
from typing import List, Dict

# Patterns macro: % / bps / MoM / YoY / trillions etc.
PATTERNS = {
    "percent": r"(-?\d+(?:\.\d+)?)\s?%",
    "bps": r"(-?\d+)\s?bps",
    "mom": r"(-?\d+(?:\.\d+)?)\s?(?:MoM|m/m)",
    "yoy": r"(-?\d+(?:\.\d+)?)\s?(?:YoY|y/y)",
    "currency": r"\$(-?\d+(?:\.\d+)?)",
    "k_jobs": r"(\d+)[ ]?K(?=\s?jobs|\s?payrolls)",
    "million": r"(\d+(?:\.\d+)?)\s?million",
    "billion": r"(\d+(?:\.\d+)?)\s?billion",
}

def extract_numbers(text: str) -> List[Dict]:
    results = []
    for label, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            results.append({
                "type": label,
                "raw": match.group(0),
                "value": float(match.group(1)),
                "context": text[max(match.start()-40, 0): match.end()+40]
            })
    return results
