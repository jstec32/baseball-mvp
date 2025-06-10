#!/usr/bin/env python3
import json, csv
from pathlib import Path

LOG_FILE = Path(__file__).parent / "sql_chat.log"
OUT_CSV  = Path(__file__).parent / "sql_chat.csv"

if not LOG_FILE.exists():
    print(f"No log found at {LOG_FILE}")
    exit(1)

fields = ["timestamp","user_query","final_sql","row_count","attempts"]
with LOG_FILE.open("r", encoding="utf-8") as fin, \
     OUT_CSV.open("w", newline="", encoding="utf-8") as fout:

    writer = csv.DictWriter(fout, fieldnames=fields)
    writer.writeheader()

    for line in fin:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        writer.writerow({
            "timestamp":   entry.get("timestamp",""),
            "user_query":  entry.get("user_query","").replace("\n"," "),
            "final_sql":   entry.get("final_sql","").replace("\n"," "),
            "row_count":   entry.get("row_count", 0),
            "attempts":    json.dumps(entry.get("attempts",[]))
        })

print(f"Wrote {OUT_CSV} (inspect with Excel/pandas/etc.)")

import pandas as pd

df = pd.read_json("sql_chat.log", lines=True)
df["errored"] = df["attempts"].apply(lambda a: isinstance(a, list) and len(a) > 0)

# 3) overall success rate
print("Success rate:", 1 - df["errored"].mean())

# 4) top error messages
errors = (
    df[df["errored"]]
      .attempts
      .explode()                    # now each row is a dict { "sql":…, "error":… }
      .apply(lambda x: x["error"])  # extract the error message
)
print(errors.value_counts().head(10))

