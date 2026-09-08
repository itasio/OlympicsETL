import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect

from app.main import (
    ATHLETE_EVENTS_TABLE,
    COUNTRY_DEFINITIONS_TABLE,
    clean_athlete_events,
    clean_country_definitions,
    load_df_to_db,
    load_olympics_data,
    query_the_db,
    resolve_data_dir,
    validate_loaded_data,
)


class CleaningTests(unittest.TestCase):
    def test_clean_country_definitions_normalizes_deduplicates_and_updates_singapore(self):
        source = pd.DataFrame(
            {
                " NOC ": ["SIN", "SIN", "USA"],
                "Region": ["Singapore", "Singapore", "United States"],
                "Notes": [None, None, None],
            }
        )

        with redirect_stdout(io.StringIO()):
            cleaned = clean_country_definitions(source)

        self.assertEqual(["noc", "region", "notes"], list(cleaned.columns))
        self.assertEqual(["SGP", "USA"], cleaned["noc"].tolist())
        self.assertEqual("SIN", source.loc[0, " NOC "])

    def test_clean_athlete_events_filters_invalid_rows_and_adds_derived_columns(self):
        source = pd.DataFrame(
            [
                {
                    "ID": 1,
                    "Name": "Medalist",
                    "Age": 20,
                    "Height": 200,
                    "Weight": 80,
                    "Year": 2000,
                    "NOC": "USA",
                    "Team": "United States",
                    "Medal": "Gold",
                },
                {
                    "ID": 2,
                    "Name": "Unknown country",
                    "Age": 21,
                    "Height": 180,
                    "Weight": 75,
                    "Year": 2004,
                    "NOC": "XXX",
                    "Team": "Unknown",
                    "Medal": None,
                },
                {
                    "ID": 3,
                    "Name": "Invalid age",
                    "Age": -1,
                    "Height": 170,
                    "Weight": 60,
                    "Year": 2008,
                    "NOC": "USA",
                    "Team": "United States",
                    "Medal": None,
                },
            ]
        )
        countries = pd.DataFrame({"noc": ["USA"]})

        with redirect_stdout(io.StringIO()):
            cleaned = clean_athlete_events(source, countries)

        self.assertEqual([1], cleaned["id"].tolist())
        self.assertEqual(20.0, cleaned.iloc[0]["bmi"])
        self.assertTrue(bool(cleaned.iloc[0]["won_medal"]))
        self.assertNotIn("bmi", source.columns)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

    def tearDown(self):
        self.engine.dispose()

    def test_load_df_to_db_is_non_destructive_by_default_and_replaceable(self):
        original = pd.DataFrame({"value": [1]})
        replacement = pd.DataFrame({"value": [2, 3]})

        with redirect_stdout(io.StringIO()):
            load_df_to_db(original, "example", db_engine=self.engine)
            load_df_to_db(replacement, "example", db_engine=self.engine)

        unchanged = pd.read_sql_table("example", self.engine)
        self.assertEqual([1], unchanged["value"].tolist())

        with redirect_stdout(io.StringIO()):
            load_df_to_db(
                replacement,
                "example",
                replace_if_exists=True,
                db_engine=self.engine,
            )

        replaced = pd.read_sql_table("example", self.engine)
        self.assertEqual([2, 3], replaced["value"].tolist())

    def test_load_pipeline_replaces_data_and_is_idempotent(self):
        countries = pd.DataFrame(
            {"NOC": ["USA"], "region": ["United States"], "notes": [None]}
        )
        athletes = pd.DataFrame(
            [
                {
                    "ID": 1,
                    "Name": "Athlete",
                    "Sex": "F",
                    "Age": 25,
                    "Height": 175,
                    "Weight": 65,
                    "Team": "United States",
                    "NOC": "USA",
                    "Games": "2016 Summer",
                    "Year": 2016,
                    "Season": "Summer",
                    "City": "Rio de Janeiro",
                    "Sport": "Swimming",
                    "Event": "Example event",
                    "Medal": "Gold",
                }
            ]
        )
        second_athlete = athletes.iloc[0].copy()
        second_athlete["ID"] = 2
        second_athlete["Name"] = "Second Athlete"
        updated_athletes = pd.concat(
            [athletes, second_athlete.to_frame().T],
            ignore_index=True,
        )

        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            countries.to_csv(data_dir / "country_definitions.csv", index=False)
            athletes.to_csv(data_dir / "athlete_events.csv", index=False)

            with redirect_stdout(io.StringIO()):
                table_name = load_olympics_data(data_dir, db_engine=self.engine)

            updated_athletes.to_csv(data_dir / "athlete_events.csv", index=False)
            with redirect_stdout(io.StringIO()):
                load_olympics_data(
                    data_dir,
                    replace_if_exists=True,
                    db_engine=self.engine,
                )
                load_olympics_data(
                    data_dir,
                    replace_if_exists=True,
                    db_engine=self.engine,
                )
                query_the_db(table_name, db_engine=self.engine)
                validated_table_name = validate_loaded_data(
                    table_name,
                    db_engine=self.engine,
                )

        self.assertEqual(ATHLETE_EVENTS_TABLE, table_name)
        self.assertEqual(ATHLETE_EVENTS_TABLE, validated_table_name)
        self.assertTrue(inspect(self.engine).has_table(ATHLETE_EVENTS_TABLE))
        self.assertTrue(inspect(self.engine).has_table(COUNTRY_DEFINITIONS_TABLE))
        self.assertEqual(2, len(pd.read_sql_table(ATHLETE_EVENTS_TABLE, self.engine)))
        self.assertEqual(1, len(pd.read_sql_table(COUNTRY_DEFINITIONS_TABLE, self.engine)))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

    def tearDown(self):
        self.engine.dispose()

    @staticmethod
    def valid_athletes() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "noc": ["USA"],
                "age": [25],
                "height": [175],
                "weight": [65],
                "year": [2016],
            }
        )

    @staticmethod
    def valid_countries() -> pd.DataFrame:
        return pd.DataFrame({"noc": ["USA"]})

    def load_validation_tables(
        self,
        athletes: pd.DataFrame | None = None,
        countries: pd.DataFrame | None = None,
    ) -> None:
        athlete_data = athletes if athletes is not None else self.valid_athletes()
        country_data = countries if countries is not None else self.valid_countries()

        athlete_data.to_sql(
            ATHLETE_EVENTS_TABLE,
            self.engine,
            index=False,
            if_exists="replace",
        )
        country_data.to_sql(
            COUNTRY_DEFINITIONS_TABLE,
            self.engine,
            index=False,
            if_exists="replace",
        )

    def test_validate_loaded_data_accepts_valid_tables(self):
        self.load_validation_tables()

        with redirect_stdout(io.StringIO()):
            table_name = validate_loaded_data(db_engine=self.engine)

        self.assertEqual(ATHLETE_EVENTS_TABLE, table_name)

    def test_validate_loaded_data_rejects_missing_tables(self):
        with self.assertRaisesRegex(
            ValueError,
            "Required database tables are missing: athlete_events, country_definitions",
        ):
            validate_loaded_data(db_engine=self.engine)

    def test_validate_loaded_data_rejects_empty_tables(self):
        empty_athletes = pd.DataFrame(
            columns=["noc", "age", "height", "weight", "year"]
        )
        empty_countries = pd.DataFrame(columns=["noc"])
        self.load_validation_tables(empty_athletes, empty_countries)

        with self.assertRaises(ValueError) as context:
            validate_loaded_data(db_engine=self.engine)

        error_message = str(context.exception)
        self.assertIn("athlete table is empty", error_message)
        self.assertIn("country table is empty", error_message)

    def test_validate_loaded_data_rejects_unknown_noc(self):
        athletes = self.valid_athletes()
        athletes.loc[0, "noc"] = "XXX"
        self.load_validation_tables(athletes=athletes)

        with self.assertRaisesRegex(ValueError, "unknown NOC"):
            validate_loaded_data(db_engine=self.engine)

    def test_validate_loaded_data_rejects_invalid_numeric_values(self):
        athletes = self.valid_athletes()
        athletes.loc[0, "age"] = -1
        self.load_validation_tables(athletes=athletes)

        with self.assertRaisesRegex(ValueError, "invalid values"):
            validate_loaded_data(db_engine=self.engine)


class PathTests(unittest.TestCase):
    def test_resolve_data_dir_rejects_missing_directory(self):
        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            resolve_data_dir("/definitely/not/an/olympics/data/directory")


if __name__ == "__main__":
    unittest.main()
