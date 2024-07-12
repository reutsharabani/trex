import asyncio
import hashlib
import os
import tempfile
import logging
import io

from pyppeteer import launch

from PIL import Image
import imagehash

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def md5(s):
    if not s:
        return None
    bs = s.encode('utf-8')
    return md5_bytes(bs)


def md5_bytes(bs):
    if not bs:
        return None
    md5_hash = hashlib.md5()
    md5_hash.update(bs)
    md5_hex = md5_hash.hexdigest()
    return md5_hex


async def fetch_page_content_and_screenshot(url):
    logger.debug(f'Launching browser to fetch content and screenshot for URL: {url}')
    browser = await launch(headless=True, handleSIGINT=False, handleSIGTERM=False, handleSIGHUP=False)
    page = await browser.newPage()
    await page.goto(url)
    await page.waitFor(3000)
    content = await page.content()
    screenshot = await page.screenshot({'fullPage': True})
    await browser.close()
    logger.debug(f'Fetched content and screenshot for URL: {url}')
    return content, screenshot


def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} days")
    if hours > 0:
        parts.append(f"{hours}hours")
    if minutes > 0:
        parts.append(f"{minutes} minutes")
    if seconds > 0:
        parts.append(f"{seconds} seconds")

    return ", ".join(parts)


def upload_to_slack(client, channel_id, screenshot, filename, initial_comment):
    file_path = os.sep.join([tempfile.gettempdir(), filename])
    with open(file_path, 'wb+') as f:
        f.write(screenshot)
    try:
        client.files_upload_v2(
            channels=channel_id,
            file=file_path,
            filename=filename,
            title=f"Screenshot for {filename}",
            initial_comment=initial_comment
        )
    finally:
        os.remove(file_path)


def format_datetime(dt):
    return f"<!date^{int(dt.timestamp())}^{{date_long_pretty}} at {{time_secs}}|{dt.isoformat()}>"


def compare_images(image_bytes1, image_bytes2):
    image1 = Image.open(io.BytesIO(image_bytes1))
    image2 = Image.open(io.BytesIO(image_bytes2))

    hash1 = imagehash.phash(image1, hash_size=32)
    hash2 = imagehash.phash(image2, hash_size=32)

    return hash1 - hash2

