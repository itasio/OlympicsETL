import pandas as pd
from sqlalchemy import create_engine


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


def send_df_to_db(df_to_load):
    # create DB connection
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/postgres")

    # load data into table
    df_to_load.to_sql(
        "athlete_events",
        engine,
        if_exists="replace",
        index=False
    )

    return engine


if __name__ == '__main__':
    # Read CSV
    df = pd.read_csv("data/athlete_events.csv")

    # Do some cleaning
    df = clean_my_dataset(df)


    print("Cleaned Dataset")
    print(df.head(20))

    # The 3 oldest athletes to ever have won a medal
    df.query("won_medal == True")
    print(df.query("won_medal == True").head(20))
    oldest_medalists = df[df["won_medal"] == True].sort_values("age", ascending=False)

    print("Oldest Medalists")
    print(oldest_medalists[["name", "age", "team"]].head(3))


    # Number of unique (different) athletes competed over time by country
    athletes_teams = df[["id", "team"]].drop_duplicates()
    ath_by_country = athletes_teams.groupby("team")["id"].count()

    print("Unique athletes by country all those years")
    print(ath_by_country.head(20))

    # The number of medals won by country sorted
    medals_per_country = (df[df["medal"].notna()]
                          .groupby("team")["medal"].count()
                          .sort_values(ascending=False))

    print("Medals per country sorted")
    print(medals_per_country.head(20))

    # load df to db
    the_engine = send_df_to_db(df)

    # Query the db

    # query = """
    #         SELECT name, team
    #         FROM athlete_events
    #         limit 10
    #         """
    # result = pd.read_sql(query, the_engine)
    # print(result)


    # Who is the athlete that has won the most medals

    # query = """
    #          SELECT name, COUNT(medal) as medals_won
    #          FROM athletes_events
    #          WHERE medal IS NOT NULL
    #          GROUP BY name
    #          ORDER BY medals_won DESC
    #          limit 1
    #         """
    # result = pd.read_sql(query, the_engine)
    # print(result)


