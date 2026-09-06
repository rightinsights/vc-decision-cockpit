from app.config import BACKEND_DIR, Settings


def test_relative_sqlite_resolves_against_backend_dir():
    url = Settings(database_url="sqlite:///./data/app.db", _env_file=None).resolved_database_url()
    assert url.startswith("sqlite:///") and url.endswith("/data/app.db")
    assert BACKEND_DIR.as_posix() in url


def test_plain_postgres_urls_get_psycopg_driver():
    s = Settings(database_url="postgresql://u:p@host/db?sslmode=require", _env_file=None)
    assert s.resolved_database_url() == "postgresql+psycopg://u:p@host/db?sslmode=require"
    s = Settings(database_url="postgres://u:p@host/db", _env_file=None)
    assert s.resolved_database_url() == "postgresql+psycopg://u:p@host/db"
    s = Settings(database_url="postgresql+psycopg://u:p@host/db", _env_file=None)
    assert s.resolved_database_url() == "postgresql+psycopg://u:p@host/db"
