from datetime import time

from Query_Generator.Scripts.pitcher_season_stats import main_pitcher_season_stats
from Query_Generator.Scripts.team_game_stats import fetch_yesterday_team_stats_and_append_to_s3
from Query_Generator.Scripts.team_record_generation import update_team_records, fetch_mlb_game_data, \
    compute_team_records, upsert_team_records
from scripts.Hitter_Report_Card.Data_Pipeline_Automation.Hitter_Season_Stats_Automated import main_hitter_season_stats
from scripts.Hitter_Report_Card.Data_Pipeline_Automation.Pitch_Data_Daily_Ingestion import \
    run_statcast_pipeline_for_date
from scripts.Hitter_Report_Card.Data_Pipeline_Automation.boxscore_auto_pipeline import boxscore_intake
from scripts.Hitter_Report_Card.Data_Pipeline_Automation.daily_top_performers import run_top_performers_email_pipeline
from scripts.Hitter_Report_Card.Data_Pipeline_Automation.game_log_automate import game_log_generation
from scripts.Hitter_Report_Card.Data_Pipeline_Automation.game_score_pipeline import run_game_score_pipeline, \
    merge_daily_pitch_box

from datetime import datetime, timedelta
import time

from scripts.Hitter_Report_Card.Data_Pipeline_Automation.pitcher_game_logs import backfill_pitcher_game_logs

# Specify your missing dates here
yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
print(yesterday)
missing_dates = [yesterday]

def process_data_for_dates(dates):
    log = ["Starting Baseball MVP Data Backfill Pipeline"]

    try:
        for date_str in dates:
            print(f"\n Processing date: {date_str}")
            log.append(f"Processing {date_str}")

            # Statcast pipeline and boxscore update
            run_statcast_pipeline_for_date(date_str)
            log.append(f"Statcast ingestion complete for {date_str}")
            boxscore_intake(date_str)
            log.append(f"Box score intake complete for {date_str}")

            # Update Hitter Season Stats & game log
            if date_str == dates[0]:  # Only update once
                main_hitter_season_stats()
                log.append("Hitter season stats updated")
            game_log_generation(date_str)
            log.append(f"Game logs generated for {date_str}")
            merge_daily_pitch_box(date_str)
            log.append(f"Merged daily pitchbox for {date_str}")

            # Run game score pipeline and top performers email
            run_game_score_pipeline()
            log.append(f"Game scores calculated for {date_str}")
            print("Waiting for S3 upload to finalize...")
            time.sleep(20)
            run_top_performers_email_pipeline(date_str)
            log.append(f"Top performers email/report sent for {date_str}")
            today = datetime.today().year
            main_pitcher_season_stats(2025, 2025)
            backfill_pitcher_game_logs(date_str,date_str)
            #process team records
            df_games = fetch_mlb_game_data()
            df_records = compute_team_records(df_games)
            print("Computed team records (first few rows):")
            print(df_records.head(), "\n")
            upsert_team_records(df_records)
            fetch_yesterday_team_stats_and_append_to_s3()

    except Exception as e:
        log.append(f"Error during backfill pipeline: {e}")
        print(f"[ERROR] {e}")

    finally:
        final_log = "\n".join(log)
        print("\n=== Backfill Pipeline Log ===")
        print(final_log)

# ===> Then run this:
process_data_for_dates(missing_dates)
