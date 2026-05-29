import pandas as pd
from db import engine
from sqlalchemy import inspect


def clean_my_dataset(df_to_clean: pd.DataFrame) -> pd.DataFrame:
    df_to_clean.columns = df_to_clean.columns.str.strip().str.lower().str.replace(" ", "_")
    df_to_clean = df_to_clean.drop_duplicates()

    df_to_clean = df_to_clean[df_to_clean["age"] >= 0]
    df_to_clean = df_to_clean[df_to_clean["height"] >= 0]
    df_to_clean = df_to_clean[df_to_clean["weight"] >= 0]
    df_to_clean = df_to_clean[df_to_clean["year"] >= 1896]

    df_to_clean["bmi"] = (df_to_clean["weight"] / ((df_to_clean["height"] / 100) ** 2)).round(3)
    df_to_clean["won_medal"] = df_to_clean["medal"].notna()
    return df_to_clean



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


def load_df_to_db(df, tbl_name):
    inspector = inspect(engine)

    if inspector.has_table(tbl_name):
        print(f"\nTable '{tbl_name}' already exists.\n")
    else:
        df.to_sql(tbl_name, engine, index=False)
        print(f"\nTable '{tbl_name}' created.\n")


if __name__ == '__main__':
    # Read CSV
    df = pd.read_csv("data/athlete_events.csv")

    # Do some cleaning
    df = clean_my_dataset(df)

    print("Cleaned Dataset\n")
    print(df.head(5))

    # Make some demo queries to dataframe
    query_the_df(df)


    # load df to db if it does not exist
    tbl_name = "athlete_events"
    load_df_to_db(df, tbl_name)


    # Query the db
    query_the_db(tbl_name)

