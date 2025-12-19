import os
from dotenv import load_dotenv

if os.getenv("DOCKER"):
    load_dotenv(".env.docker")
else:
    load_dotenv(".env.local")

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
SQLALCHEMY_DUMP = os.getenv("SQLALCHEMY_DUMP")
