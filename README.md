# Olympics ETL

A demonstration ETL pipeline that cleans Olympic Games CSV data from
[Maven analytics](https://mavenanalytics.io/data-playground/120-years-of-olympic-history) and loads
`athlete_events` and `country_definitions` into PostgreSQL.

Airflow integration is included for learning and orchestration demonstration;
the checked-in static data does not require periodic scheduling.

## Architecture

- pandas extracts and transforms the CSV data
- PostgreSQL stores the cleaned tables
- Airflow optionally orchestrates loading and validation

## Quick start

```
cp .env.example .env
docker compose up airflow-init
docker compose up -d airflow-webserver airflow-scheduler
```

Open http://localhost:8080 and trigger `olympics_etl`.

## Run without Airflow

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres
python -m app.main
```

## Tests

```
python -m unittest discover -s tests -v
docker compose config -q
```

## Limitations

The source files are static and the DAG is manually triggered. The current
Airflow 2.9.3 stack is for local development only.