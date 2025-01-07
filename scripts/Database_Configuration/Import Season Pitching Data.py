from pybaseball import pitching_stats

# get all of this season's pitching data so far
data = pitching_stats(2023)

print(data.columns)