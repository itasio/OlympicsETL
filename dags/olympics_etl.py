from datetime import datetime, timedelta, timezone

from airflow.decorators import dag, task


@dag(
    dag_id="olympics_etl",
    description="Clean Olympics CSV data and load it into PostgreSQL",
    schedule=None,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "olympics-etl",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["olympics", "etl"],
)
def olympics_etl():
    @task(task_id="load_olympics_data")
    def load_data() -> str:
        from app.main import load_olympics_data

        return load_olympics_data(replace_if_exists=True)

    @task(task_id="query_olympics_data")
    def query_loaded_data(table_name: str) -> None:
        from app.main import query_the_db

        query_the_db(table_name)

    query_loaded_data(load_data())


olympics_etl_dag = olympics_etl()
