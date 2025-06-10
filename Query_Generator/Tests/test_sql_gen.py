import pytest
from pathlib import Path
from Query_Generator.wrapper.llm_sql import SQLSandbox

PROMPT = str(Path(__file__).parent.parent / "wrapper" / "sql_generation.txt")

@pytest.fixture
def sandbox():
    return SQLSandbox(PROMPT)

# -- Basic sanity: uses only allowed tables/columns
def test_no_illegal_columns(sandbox):
    q   = "List all pitchers with more than 50 strikeouts in May 2025."
    sql = sandbox.ask_sql(q).lower()

    # Must either cast game_date to DATE or use EXTRACT(year)/EXTRACT(month)
    has_date_cast = "game_date::date" in sql
    has_extract   = "extract(year" in sql and "extract(month" in sql
    assert has_date_cast or has_extract, (
        "Date filter must use game_date::date or EXTRACT(year)/EXTRACT(month) from game_date"
    )

    # Ensure we didn’t reference any totally invalid columns
    for bad in ("foobar", "dummy_col", "nonexistent"):
        assert bad not in sql, f"Found illegal column reference: {bad}"

# -- Name lookup rule
def test_name_join_pattern(sandbox):
    q   = "What is Tarik Skubal's monthly ERA so far?"
    sql = sandbox.ask_sql(q).lower()
    # collapse all whitespace to single spaces
    norm_sql = ' '.join(sql.split())

    # it must JOIN players AS pl
    assert 'join players as pl' in norm_sql, f"Expected JOIN players AS pl, got:\n{norm_sql}"

    # it must use the alias 'pl' in the CONCAT
    assert 'concat(pl."first_name",' in norm_sql, (
        "Name join must use CONCAT(pl.\"First_Name\", ' ', pl.\"Last_Name\")"
    )

# -- Date filtering pattern
def test_date_filter(sandbox):
    q = "Show Jeremy Peña's strikeouts in April 2025."
    sql = sandbox.ask_sql(q).lower()
    has_date_cast = "game_date::date" in sql
    has_extract = "extract(year" in sql and "extract(month" in sql
    assert has_date_cast or has_extract, (
        "Date filter must use game_date::date = 'YYYY-MM-DD' "
        "or EXTRACT(year)/EXTRACT(month) from game_date"
    )

# -- Key usage
def test_key_mlbam_use(sandbox):
    q = "Get the scaled game score for Max Scherzer."
    sql = sandbox.ask_sql(q).lower()
    assert "key_mlbam" in sql

def test_plate_appearances_qualifier(sandbox):
    q   = "List the top 5 by wrc+ this season."
    sql = sandbox.ask_sql(q).lower()
    # Must include the nested plate_appearances filter
    assert "hs.plate_appearances >=" in sql
    assert "select max(hs2.games) * 3.1" in sql

def test_hitting_table_used(sandbox):
    q   = "Who has the highest ops this year?"
    sql = sandbox.ask_sql(q).lower()
    assert "from hitter_season_statistics as hs" in sql

def test_csv_table_query(sandbox):
    q   = "What was the average home_score per venue in 2025?"
    sql = sandbox.ask_sql(q).lower()
    assert "from mlb_game_data_2025 as g" in sql
    assert "avg(g.home_score)" in sql