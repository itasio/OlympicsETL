import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


@dataclass(frozen=True)
class Settings:
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_db: str

    @classmethod
    def from_environment(cls) -> "Settings":
        port = _required_environment_variable("POSTGRES_PORT")
        try:
            parsed_port = int(port)
        except ValueError as exc:
            raise RuntimeError("POSTGRES_PORT must be an integer") from exc

        return cls(
            postgres_user=_required_environment_variable("POSTGRES_USER"),
            postgres_password=_required_environment_variable("POSTGRES_PASSWORD"),
            postgres_host=_required_environment_variable("POSTGRES_HOST"),
            postgres_port=parsed_port,
            postgres_db=_required_environment_variable("POSTGRES_DB"),
        )

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read and validate database settings on first application use."""
    return Settings.from_environment()
