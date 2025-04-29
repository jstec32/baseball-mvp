from datetime import time

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

# Specify your missing dates here
missing_dates = [
    "2025-04-28"
]

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

    except Exception as e:
        log.append(f"Error during backfill pipeline: {e}")
        print(f"[ERROR] {e}")

    finally:
        final_log = "\n".join(log)
        print("\n=== Backfill Pipeline Log ===")
        print(final_log)

# ===> Then run this:
process_data_for_dates(missing_dates)
