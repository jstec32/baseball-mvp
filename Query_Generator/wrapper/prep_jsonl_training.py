import pandas as pd
import json


df = pd.read_csv("/Query_Generator/wrapper/Data_Files/Sheet 1-sql_chat.csv")

# Filter: only rows with Gold SQL
df = df[df["Gold SQL"].notna() & (df["Gold SQL"].str.strip() != "")]

# Output path
output_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/Query_Generator/wrapper/finetune_data.jsonl"

# Write JSONL
with open(output_path, "w") as f:
    for _, row in df.iterrows():
        item = {
            "messages": [
                {"role": "user", "content": row["user_query"].strip()},
                {"role": "assistant", "content": row["Gold SQL"].strip()}
            ]
        }
        f.write(json.dumps(item) + "\n")

print(f"Saved {len(df)} examples to {output_path}")
