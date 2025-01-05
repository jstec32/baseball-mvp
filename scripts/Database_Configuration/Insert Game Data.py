from scripts.Database_Configuration.Get_Game_Data import gather_games_data,transform_games_data
import pandas as pd
import psycopg2

mlb_teams = [
     "ARI"
]

def populate_games_table(conn, df):

    insert_query = """
    INSERT INTO games (
        game_id,
        game_date,
        home_team,
        away_team,
        winning_team,
        final_score,
        year,
        tm,
        opp,
        wl,
        raw_date
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (game_id)
    DO NOTHING;
    """

    with conn.cursor() as cursor:
        for _, row in df.iterrows():



            cursor.execute(
                insert_query,
                (
                    row["game_id"],
                    row["game_date"],       # Make sure this is a datetime.date or None
                    row["home_team"],
                    row["away_team"],
                    row["winning_team"],
                    row["final_score"],
                    int(row["Year"]) if not pd.isnull(row["Year"]) else None,
                    row["Tm"],
                    row["Opp"],
                    row["W/L"],
                    row["raw_date"]
                )
            )
        conn.commit()
    print("Data from DataFrame inserted into `games` table!")


def main():

    conn = psycopg2.connect(
        host = "aws-0-us-east-2.pooler.supabase.com",
        database = "postgres",
        user = "postgres.chcovbrcpmlxyauansqe",
        password = "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
        port = 5432  # Default PostgreSQL port)
    )

    raw_games_df = gather_games_data(mlb_teams, 2021, 2021)
    transformed_df = transform_games_data(raw_games_df)
    populate_games_table(conn, transformed_df)

    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()

