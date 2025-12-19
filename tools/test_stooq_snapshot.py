import requests

base = "https://stooq.com/q/l/"
for sym in ["cl.f", "gc.f", "zn.f", "zt.f", "gg.f", "eurusd"]:
    r = requests.get(base, params={"s": sym, "i": "5"}, timeout=10, headers={"User-Agent":"KMCO-Test/1.0"})
    print(sym, r.status_code, (r.headers.get("Content-Type") or ""), (r.text or "")[:80].replace("\n","\\n"))
import requests

BASE = "https://stooq.com/q/l/"

symbols = [
    "cl.f",     # WTI
    "gc.f",     # Gold
    "zn.f",     # US 10Y
    "zt.f",     # US 2Y
    "gg.f",     # Bund
    "eurusd",   # FX
]

headers = {
    "User-Agent": "KMCO-Test/1.0",
    "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.1",
}

for sym in symbols:
    try:
        r = requests.get(
            BASE,
            params={"s": sym, "i": "5"},
            headers=headers,
            timeout=10,
        )
        print(
            sym,
            "STATUS=", r.status_code,
            "CT=", r.headers.get("Content-Type"),
            "HEAD=", (r.text[:120] if r.text else "EMPTY").replace("\n", "\\n")
        )
    except Exception as e:
        print(sym, "EXCEPTION", type(e).__name__, str(e))
