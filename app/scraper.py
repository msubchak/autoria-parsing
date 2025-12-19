import asyncio
import aiohttp
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup, Tag
from app.db import AsyncSessionLocal, init_db
from app.models import Car
from sqlalchemy.dialects.postgresql import insert


URL = "https://auto.ria.com/uk/search/?indexName=auto"
PHONE_API_BASE_URL = "https://auto.ria.com/bff/final-page/public/auto/popUp/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_num_pages(page_soup: Tag) -> int:
    pages = page_soup.select(".pagination .page-link")
    if not pages:
        return 1
    last_page = pages[-1].get_text(strip=True)
    last_page_number = int(last_page.replace("\xa0", ""))
    return last_page_number


def phone_payload(car_soup: Tag) -> dict | None:
    try:
        scripts = car_soup.find_all("script")
        for script in scripts:
            if script.string and "autoPhone" in script.string:
                match = re.search(r'\{"blockId":"autoPhone".+?\}\}', script.string)
                if match:
                    json_str = match.group(0)
                    try:
                        payload = json.loads(json_str)
                        payload.update({
                            "langId": 4,
                            "device": "desktop-web"
                        })
                        return payload
                    except json.JSONDecodeError:
                        clean_json = re.sub(r',(\s*[\]\}])', r'\1', json_str)
                        return json.loads(clean_json)

        btn = car_soup.find(attrs={"data-analytics-data": True})
        if btn:
            return json.loads(btn["data-analytics-data"])
    except Exception:
        pass
    return None


def get_vin(car: Tag) -> str | None:
    vin_span = car.select_one(".badge-template span.ws-pre-wrap.badge")
    if vin_span:
        vin = vin_span.get_text(strip=True)
        if re.fullmatch(r"[A-Z0-9]+", vin):
            return vin
    return None


async def get_phone_number(session, payload: dict, url: str) -> str | None:
    if not payload:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": url,
        "Origin": "https://auto.ria.com"
    }

    try:
        async with session.post(PHONE_API_BASE_URL, headers=headers, json=payload, timeout=10) as response:
            if response.status == 200:
                res_json = await response.json()
                phone_str = res_json.get("additionalParams", {}).get("phoneStr")
                return phone_str
    except:
        pass
    return None


async def parsing_single_car(session, car: Tag, url: str) -> dict:
    try:
        title = car.select_one("#sideTitleTitle .titleM").get_text(strip=True)
    except AttributeError:
        title = None

    try:
        price_text = car.select_one("#sidePrice .titleL").get_text(strip=True)
        price_usd = int(price_text.replace("$", "").replace("\xa0", ""))
    except AttributeError:
        price_usd = None

    try:
        odometer_text = car.select_one("#basicInfoTableMainInfo0 .ws-pre-wrap").get_text(strip=True)
        odometer = int(
            odometer_text.replace("тис. км", "000").replace("км", "").replace(" ", "").replace("Безпробігу", "0"))
    except AttributeError:
        odometer = None

    try:
        username = car.select_one("#sellerInfoUserName .titleM").get_text(strip=True)
    except AttributeError:
        username = None

    try:
        payload = phone_payload(car)
        phone_number = await get_phone_number(session, payload, url)
        if phone_number:
            phone_number = re.sub(r"\D", "", phone_number)
            phone_number = int(f"38{phone_number}")
    except AttributeError:
        phone_number = None

    try:
        image_url_first = car.select_one(".carousel__track .picture img")
        image_url = image_url_first.get("data-src")
    except AttributeError:
        image_url = None

    try:
        images_count = int(car.select_one(".common-badge.alpha.medium").get_text().split(" ")[2])
    except AttributeError:
        images_count = None

    try:
        car_number = car.select_one(".car-number .ws-pre-wrap").get_text(strip=True)
    except AttributeError:
        car_number = None

    try:
        car_vin = get_vin(car)
    except AttributeError:
        car_vin = None

    return {
        "url": url,
        "title": title,
        "price_usd": price_usd,
        "odometer": odometer,
        "username": username,
        "phone_number": phone_number,
        "image_url": image_url,
        "images_count": images_count,
        "car_number": car_number,
        "car_vin": car_vin,
        "datetime_found": datetime.utcnow(),
    }


async def fetch_car(session, semaphore, url):
    async with semaphore:
        try:
            await asyncio.sleep(0.3)

            async with session.get(url, timeout=20) as car_resp:
                if car_resp.status != 200:
                    return None

                inner_soup = BeautifulSoup(await car_resp.text(), "html.parser")
                banner = inner_soup.select_one("#bannerStatusText")
                if banner:
                    status_spans = banner.select("span.common-text.ws-pre-wrap")
                    if any("видалене" in span.get_text(strip=True) for span in status_spans):
                        return None

                data = await parsing_single_car(session, inner_soup, url)
                return data
        except Exception:
            return None


async def get_home_car() -> list[dict]:
    dublicate_sets = set()
    all_tasks = []
    semaphore = asyncio.Semaphore(2)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(URL) as response:
            text = await response.text()
            first_page_soup = BeautifulSoup(text, "lxml")
            num_pages = get_num_pages(first_page_soup)

        for page in range(num_pages):
            page_url = f"{URL}&page={page}"
            try:
                async with session.get(page_url) as response:
                    page_soup = BeautifulSoup(await response.text(), "lxml")
                    cars = page_soup.select("a.link.product-card.horizontal")

                    for car in cars:
                        full_link = "https://auto.ria.com" + car.get("href")

                        if "/newauto/" in full_link:
                            continue
                        if full_link in dublicate_sets:
                            continue

                        dublicate_sets.add(full_link)
                        task = asyncio.create_task(fetch_car(session, semaphore, full_link))
                        all_tasks.append(task)
            except Exception:
                continue

        page_results = await asyncio.gather(*all_tasks)

    valid_results = [item for item in page_results if item is not None]
    return valid_results


async def save_to_db(cars_data: list[dict]) -> None:
    async with AsyncSessionLocal() as db_session:
        for car_data in cars_data:
            statement = insert(Car).values(**car_data).on_conflict_do_nothing(index_elements=['url'])
            await db_session.execute(statement)
        await db_session.commit()


async def main():
    await init_db()
    data = await get_home_car()
    await save_to_db(data)
