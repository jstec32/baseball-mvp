from pybaseball import statcast
import os
import uuid

# Output path
OUTPUT_DIR = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


SEASONS = {
    "2022": ("2022-04-07", "2022-10-05")
}


RENAME_MAP = {
    "game_pk": "game_id",
    "pitcher": "pitcher_id",
    "batter": "batter_id",
    "pitch_name": "pitch_type",
    "release_speed": "release_speed",
    "release_spin_rate": "release_spin_rate",
    "release_pos_x": "release_pos_x",
    "release_pos_y": "release_pos_y",
    "release_pos_z": "release_pos_z",
    "pfx_x": "pfx_x",
    "pfx_z": "pfx_z",
    "plate_x": "plate_x",
    "plate_z": "plate_z",
    "zone": "zone",
    "events": "events",
    "description": "description",
    "launch_speed": "launch_speed",
    "launch_angle": "launch_angle",
    "hit_distance_sc": "hit_distance_sc",
    "effective_speed": "effective_speed",
    "spin_axis": "spin_axis",
    "stand": "stand",
    "p_throws": "p_throws",
    "inning": "inning",
    "inning_topbot": "inning_topbot",
    "game_date": "game_date",
    "on_1b": "on_1b",
    "on_2b": "on_2b",
    "on_3b": "on_3b",
    "outs_when_up": "outs_when_up",
    "hc_x": "hc_x",
    "hc_y": "hc_y",
    "woba_value": "woba_value",
    "woba_denom": "woba_denom",
    "delta_run_exp": "delta_run_exp",
    "delta_home_win_exp": "delta_home_win_exp"
}

def process_statcast_data(df):
    df = df.rename(columns=RENAME_MAP)
    df["pitch_id"] = [uuid.uuid4().hex for _ in range(len(df))]
    return df


for year, (start_date, end_date) in SEASONS.items():
    print(f"Downloading {year} data ({start_date} to {end_date})...")
    try:
        df_raw = statcast(start_date, end_date)
        if df_raw.empty:
            print(f"No data found for {year}")
            continue

        df = process_statcast_data(df_raw)
        output_file = os.path.join(OUTPUT_DIR, f"statcast_pitch_data_{year}.csv")
        df.to_csv(output_file, index=False)
        print(f"Saved {len(df)} rows to {output_file}")
    except Exception as e:
        print(f"Error downloading {year}: {e}")
