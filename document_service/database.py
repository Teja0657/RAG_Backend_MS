import os
import urllib.parse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


# ==========================================================
# DATABASE CONFIGURATION
# ==========================================================

DB_USER = os.getenv(
    "MYSQL_USER",
    "root"
)

DB_PASSWORD = os.getenv(
    "MYSQL_PASSWORD",
    ""
)

DB_HOST = os.getenv(
    "MYSQL_HOST",
    "localhost"
)

DB_PORT = os.getenv(
    "MYSQL_PORT",
    "3306"
)

DB_NAME = os.getenv(
    "MYSQL_DATABASE",
    "rag_backend"
)

encoded_password=urllib.parse.quote_plus(DB_PASSWORD)

# ==========================================================
# DATABASE URL
# ==========================================================

DATABASE_URL = (
    f"mysql+pymysql://"
    f"{DB_USER}:{encoded_password}"
    f"@{DB_HOST}:{DB_PORT}"
    f"/{DB_NAME}"
)


# ==========================================================
# ENGINE
# ==========================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# ==========================================================
# SESSION
# ==========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ==========================================================
# BASE
# ==========================================================

Base = declarative_base()


# ==========================================================
# DATABASE DEPENDENCY
# ==========================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()