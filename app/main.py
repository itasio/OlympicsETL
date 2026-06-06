import pandas as pd
from db import engine
from sqlalchemy import inspect


def clean_athlete_events(ath_ev_df: pd.DataFrame, country_def_df: pd.DataFrame) -> pd.DataFrame:
    ath_ev_df.columns = ath_ev_df.columns.str.strip().str.lower().str.replace(" ", "_")
    ath_ev_df = ath_ev_df.drop_duplicates()

    ath_ev_df = ath_ev_df[ath_ev_df["age"] >= 0]
    ath_ev_df = ath_ev_df[ath_ev_df["height"] >= 0]
    ath_ev_df = ath_ev_df[ath_ev_df["weight"] >= 0]
    ath_ev_df = ath_ev_df[ath_ev_df["year"] >= 1896]

    ath_ev_df["bmi"] = (ath_ev_df["weight"] / ((ath_ev_df["height"] / 100) ** 2)).round(3)
    ath_ev_df["won_medal"] = ath_ev_df["medal"].notna()

    # Keep only the rows in which value of column NOC exists in country definitions

    noc_column = ath_ev_df["noc"]
    mask = noc_column.isin(country_def_df["noc"])
    print(f"\nThe rows in athlete_events.csv containing NOC values not included in\n"
          f"country_definitions.csv and hence omitted are: {(~mask).sum()} \n")

    ath_ev_df = ath_ev_df[mask]
    return ath_ev_df

def clean_country_definitions(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.drop_duplicates()

    # Alter the NOC of Singapore. It is SGP instead of SIN since 2016
    mask = (df["noc"] == "SIN") & (df["region"] == "Singapore")
    print(f"Rows changed in country definitions for Singapore naming: {mask.sum()} \n")
    df.loc[mask, "noc"] = "SGP"

    return df



def query_the_df(df):
    # The 3 oldest athletes to ever have won a medal
    oldest_medalists = df[df["won_medal"] == True].sort_values("age", ascending=False)

    print("\nOldest Medalists\n")
    print(oldest_medalists[["name", "age", "team"]].head(3))

    # Number of unique (different) athletes competed over time by country
    athletes_teams = df[["id", "team"]].drop_duplicates()
    ath_by_country = athletes_teams.groupby("team")["id"].count().sort_values(ascending=False)

    print("\nUnique athletes by country all those years sorted\n")
    print(ath_by_country.head(5))

    # The number of medals won by country sorted
    medals_per_country = (df[df["medal"].notna()]
                          .groupby("team")["medal"].count()
                          .sort_values(ascending=False))

    print("\nMedals per country sorted\n")
    print(medals_per_country.head(5))


def query_the_db(tbl_name):

    # The athletes with the most participations in olympics

    query = f"""
            SELECT name, COUNT(*) as participations
            FROM {tbl_name}
            GROUP BY name
            ORDER BY participations DESC
            limit 5
            """
    result = pd.read_sql(query, engine)

    print(f"\nQuery {tbl_name} to show the athletes with the most participations\n")
    print(result)


    # Who is the athlete that has won the most medals

    query = f"""
             SELECT name, COUNT(medal) as medals_won
             FROM {tbl_name}
             WHERE medal IS NOT NULL
             GROUP BY name
             ORDER BY medals_won DESC
             limit 5
            """
    result = pd.read_sql(query, engine)

    print(f"\nQuery {tbl_name} to show the top athletes that have won the most medals\n")
    print(result)



def load_df_to_db(df, tbl_name:str, replace_if_exists:bool=False):
    """

    :param df: the df to load
    :param tbl_name: the name of the table to be created in database
    :param replace_if_exists: if table exists in db and variable is set to true, table will be replaced, if set to false table will not be replaced. If table does not exist in db, it will be created.
    """
    inspector = inspect(engine)

    if inspector.has_table(tbl_name):
        print(f"\nTable '{tbl_name}' already exists.\n")
        print(f"Replace will is set to {replace_if_exists}\n")
        if replace_if_exists:
            df.to_sql(tbl_name, engine, index=False, if_exists="replace")
    else:
        # Table does not exist in db, create it
        df.to_sql(tbl_name, engine, index=False)
        print(f"\nTable '{tbl_name}' created.\n")

if __name__ == '__main__':
    # Read CSVs
    ath_events_df = pd.read_csv("./data/athlete_events.csv")
    country_definitions_df = pd.read_csv("./data/country_definitions.csv")

    # Do some cleaning
    country_definitions_df = clean_country_definitions(country_definitions_df)
    ath_events_df = clean_athlete_events(ath_events_df, country_definitions_df)

    print("Cleaned Dataset\n")
    print(ath_events_df.head(5))

    # Make some demo queries to dataframe
    query_the_df(ath_events_df)


    # load dfs to db
    tbl_events = "athlete_events"
    load_df_to_db(ath_events_df, tbl_events)

    tbl_countries = "country_definitions"
    load_df_to_db(country_definitions_df, tbl_countries)

    # Query the db
    query_the_db(tbl_events)

