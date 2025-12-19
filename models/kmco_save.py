import os, json, pandas as pd
from datetime import datetime

BASE_PATH = r"D:\trading\News Last 48H\kmco_pipeline"

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def save_json(data: dict, session: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(BASE_PATH, "data", "ideas")
    ensure_dir(out_dir)
    file_path = os.path.join(out_dir, f"macro_ideas_{date_str}_{session}.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved JSON: {file_path}")
    return file_path

def save_table(df: pd.DataFrame, session: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(BASE_PATH, "data", "tables")
    ensure_dir(out_dir)
    
    excel_path = os.path.join(out_dir, f"macro_table_{date_str}_{session}.xlsx")
    csv_path   = os.path.join(out_dir, f"macro_table_{date_str}_{session}.csv")

    df.to_excel(excel_path, index=False)
    df.to_csv(csv_path, index=False)

    print(f"✅ Saved Excel: {excel_path}")
    print(f"✅ Saved CSV:   {csv_path}")

    return excel_path, csv_path

def save_log(msg: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(BASE_PATH, "data", "logs")
    ensure_dir(out_dir)

    log_path = os.path.join(out_dir, f"log_{date_str}.txt")
    with open(log_path, "a") as f:
        f.write(f"{datetime.now()} — {msg}\n")

    print(f"📝 Logged: {msg}")
