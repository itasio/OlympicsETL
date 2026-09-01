import os
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
ATHLETE_EVENTS_FILE = "athlete_events.csv"
COUNTRY_DEFINITIONS_FILE = "country_definitions.csv"
ATHLETE_EVENTS_TABLE = "athlete_events"
COUNTRY_DEFINITIONS_TABLE = "country_definitions"


def clean_athlete_events(
    ath_ev_df: pd.DataFrame,
    country_def_df: pd.DataFrame,
) -> pd.DataFrame:
    ath_ev_df = ath_ev_df.copy()
    ath_ev_df.columns = ath_ev_df.columns.str.strip().str.lower().str.replace(" ", "_")
    ath_ev_df = ath_ev_df.drop_duplicates()

    ath_ev_df = ath_ev_df[
        (ath_ev_df["age"] >= 0)
        & (ath_ev_df["height"] >= 0)
        & (ath_ev_df["weight"] >= 0)
        & (ath_ev_df["year"] >= 1896)
    ].copy()    # Keep it defensively for Pandas < version 3

    ath_ev_df["bmi"] = (ath_ev_df["weight"] / ((ath_ev_df["height"] / 100) ** 2)).round(3)
    ath_ev_df["won_medal"] = ath_ev_df["medal"].notna()

    noc_column = ath_ev_df["noc"]
    mask = noc_column.isin(country_def_df["noc"])
    print(
        "\nThe rows in athlete_events.csv containing NOC values not included in\n"
        f"country_definitions.csv and hence omitted are: {(~mask).sum()} \n"
    )

    return ath_ev_df[mask].copy()


def clean_country_definitions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.drop_duplicates()

    # Singapore has used SGP rather than SIN as its NOC code since 2016.
    mask = (df["noc"] == "SIN") & (df["region"] == "Singapore")
    print(f"Rows changed in country definitions for Singapore naming: {mask.sum()} \n")
    df.loc[mask, "noc"] = "SGP"

    return df


def query_the_df(df: pd.DataFrame) -> None:
    oldest_medalists = df[df["won_medal"]].sort_values("age", ascending=False)

    print("\nOldest Medalists\n")
    print(oldest_medalists[["name", "age", "team"]].head(3))

    athletes_teams = df[["id", "team"]].drop_duplicates()
    athletes_by_country = athletes_teams.groupby("team")["id"].count().sort_values(ascending=False)

    print("\nUnique athletes by country all those years sorted\n")
    print(athletes_by_country.head(5))

    medals_per_country = (
        df[df["medal"].notna()]
        .groupby("team")["medal"]
        .count()
        .sort_values(ascending=False)
    )

    print("\nMedals per country sorted\n")
    print(medals_per_country.head(5))


def query_the_db(tbl_name: str, db_engine: Engine | None = None) -> None:
    target_engine = db_engine or get_engine()
    quoted_table_name = target_engine.dialect.identifier_preparer.quote(tbl_name)

    participations_query = text(
        f"""
        SELECT name, COUNT(*) AS participations
        FROM {quoted_table_name}
        GROUP BY name
        ORDER BY participations DESC
        LIMIT 5
        """
    )
    result = pd.read_sql(participations_query, target_engine)

    print(f"\nQuery {tbl_name} to show the athletes with the most participations\n")
    print(result)

    medals_query = text(
        f"""
        SELECT name, COUNT(medal) AS medals_won
        FROM {quoted_table_name}
        WHERE medal IS NOT NULL
        GROUP BY name
        ORDER BY medals_won DESC
        LIMIT 5
        """
    )
    result = pd.read_sql(medals_query, target_engine)

    print(f"\nQuery {tbl_name} to show the top athletes that have won the most medals\n")
    print(result)


def load_df_to_db(
    df: pd.DataFrame,
    tbl_name: str,
    replace_if_exists: bool = False,
    db_engine: Engine | None = None,
) -> None:
    """Load a DataFrame into the application database."""
    target_engine = db_engine or get_engine()
    table_exists = inspect(target_engine).has_table(tbl_name)

    if table_exists and not replace_if_exists:
        print(f"\nTable '{tbl_name}' already exists; leaving it unchanged.\n")
        return

    if_exists = "replace" if table_exists else "fail"
    df.to_sql(tbl_name, target_engine, index=False, if_exists=if_exists)
    action = "replaced" if table_exists else "created"
    print(f"\nTable '{tbl_name}' {action}.\n")


def resolve_data_dir(data_dir: str | Path | None = None) -> Path:
    configured_dir = data_dir or os.getenv("OLYMPICS_DATA_DIR") or DEFAULT_DATA_DIR
    resolved_dir = Path(configured_dir).expanduser().resolve()
    if not resolved_dir.is_dir():
        raise FileNotFoundError(f"Olympics data directory does not exist: {resolved_dir}")
    return resolved_dir


def load_olympics_data(
    data_dir: str | Path | None = None,
    replace_if_exists: bool = False,
    db_engine: Engine | None = None,
) -> str:
    """Extract, transform, and load both Olympics datasets.

    The table name return value is intentionally small so an Airflow task can pass
    it through XCom without serializing either DataFrame.
    """
    source_dir = resolve_data_dir(data_dir)
    target_engine = db_engine or get_engine()

    athlete_events_df = pd.read_csv(source_dir / ATHLETE_EVENTS_FILE)
    country_definitions_df = pd.read_csv(source_dir / COUNTRY_DEFINITIONS_FILE)

    country_definitions_df = clean_country_definitions(country_definitions_df)
    athlete_events_df = clean_athlete_events(athlete_events_df, country_definitions_df)

    print("Cleaned Dataset\n")
    print(athlete_events_df.head(5))
    query_the_df(athlete_events_df)

    load_df_to_db(
        athlete_events_df,
        ATHLETE_EVENTS_TABLE,
        replace_if_exists=replace_if_exists,
        db_engine=target_engine,
    )
    load_df_to_db(
        country_definitions_df,
        COUNTRY_DEFINITIONS_TABLE,
        replace_if_exists=replace_if_exists,
        db_engine=target_engine,
    )

    return ATHLETE_EVENTS_TABLE


def main() -> None:
    table_name = load_olympics_data()
    query_the_db(table_name)


if __name__ == "__main__":
    main()
