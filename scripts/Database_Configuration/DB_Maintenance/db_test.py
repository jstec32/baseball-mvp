from pybaseball import batting_stats

df = batting_stats(2025, qual=1)
print(df.columns.tolist())