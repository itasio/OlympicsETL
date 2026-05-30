## Demo project for showcasing ETL processes.

- Extract and clean dataset from modern Olympic games from  [Maven analytics](https://mavenanalytics.io/data-playground/120-years-of-olympic-history)
- Make some transformations to it
- Load it into Postgres SQL db
- Query the db

---

### To make it work

#### Create virtual environment
python -m venv .venv

#### Activate virtual environment
source .venv/bin/activate

#### Install dependencies
pip install -r requirements.txt

#### Start services
docker compose up -d

#### Run application
python main.py