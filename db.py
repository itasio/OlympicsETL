import os
from sqlalchemy import create_engine

from dotenv import load_dotenv
load_dotenv()  # loads .env from current directory

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST")
db_name = os.getenv("POSTGRES_DB")

url = f"postgresql://{user}:{password}@{host}:5432/{db_name}"
engine = create_engine(url)