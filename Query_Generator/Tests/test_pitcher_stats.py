from scripts.Hitter_Report_Card.Data_Pipeline_Automation.Pitch_Data_Daily_Ingestion import get_max_pitch_id, \
    add_balls_strikes, process_statcast_data


def run_statcast_pipeline_for_date(target_date=None):

    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    log = [f"Statcast pipeline run for {target_date}"]


    raw_data, err = fetch_statcast_data_for_day(target_date)
    if err:
        log.append(f"Error fetching data: {err}")
        return log
    elif raw_data is None or raw_data.empty:
        log.append("No data returned from Statcast API.")
        return log


    df = process_statcast_data(raw_data)
    df = add_balls_strikes(df)


    required_columns = [
        'pitch_id', 'game_id', 'game_date', 'inning', 'inning_topbot',
        'pitcher_id', 'batter_id', 'pitch_type', 'release_speed', 'release_spin_rate',
        'release_pos_x', 'release_pos_y', 'release_pos_z', 'pfx_x', 'pfx_z',
        'plate_x', 'plate_z', 'zone', 'events', 'description', 'launch_speed',
        'launch_angle', 'hit_distance_sc', 'effective_speed', 'spin_axis', 'stand',
        'p_throws', 'group', 'balls', 'strikes', 'count', 'hc_y', 'outs_when_up',
        'hc_x', 'on_1b', 'woba_value', 'delta_run_exp', 'on_3b', 'on_2b',
        'woba_denom', 'delta_home_win_exp'
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    df = df[required_columns].reset_index(drop=True)


    start_id = get_max_pitch_id()
    df["pitch_id"] = df.index + 1 + start_id


    output_path = f"statcast_pitch_data_{target_date}.csv"
    df.to_csv(output_path, index=False)
    log.append(f"CSV saved to {output_path}")