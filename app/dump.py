import os
import asyncio
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

async def dump_database():
    os.makedirs("dumps", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = f"dumps/dump_{timestamp}.sql"

    if os.getenv("ENV") == "docker":
        db_host = "db"
        db_port = "5432"
        pg_dump_path = "pg_dump"
    else:
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5433")
        pg_dump_path = os.getenv("PG_DUMP_PATH", "pg_dump")

    db_user = os.getenv("DB_USER")
    db_name = os.getenv("DB_NAME")
    db_password = os.getenv("DB_PASSWORD")

    if "\\" in pg_dump_path and not pg_dump_path.startswith('"'):
        pg_dump_path = f'"{pg_dump_path}"'

    cmd = f'{pg_dump_path} -h {db_host} -p {db_port} -U {db_user} --no-owner -F c -f "{dump_file}" {db_name}'

    process = await asyncio.create_subprocess_shell(
        cmd,
        env={**os.environ, "PGPASSWORD": db_password},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()
