import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scraper import main
from app.dump import dump_database

async def job():
    await main()


async def dump():
    await dump_database()


async def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Kiev")
    scheduler.add_job(job, trigger="cron", hour=9, minute=0)
    scheduler.add_job(dump, trigger="cron", hour=12, minute=0)
    scheduler.start()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(start_scheduler())
