import os
import sqlite3
import asyncio
import logging
from datetime import datetime
import pytz

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from apscheduler.schedulers.background import BackgroundScheduler

import utils


# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])


class DatabaseCursor:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cur = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path, timeout=20)
        self.cur = self.conn.cursor()
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cur.close()
        if exc_type or exc_val or exc_tb:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()


def init_db():
    logger.debug('Initializing database...')
    with DatabaseCursor('trex.db') as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS tracked_urls (
                url TEXT PRIMARY KEY,
                content TEXT,
                changed INTEGER,
                screenshot_before BLOB,
                screenshot_after BLOB,
                last_check_date TEXT,
                last_attempt_successful INTEGER
            )
        ''')
        logger.debug('Database initialized.')


init_db()

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.start()


def check_updates():
    logger.info('Checking for updates...')
    with DatabaseCursor('trex.db') as c:
        logger.debug('Fetching tracked URLs from database...')
        for row in c.execute('SELECT url, screenshot_after FROM tracked_urls WHERE changed = 0').fetchall():
            url, screenshot_after = row
            logger.info(f'Checking {url} for updates...')
            try:
                new_content, new_screenshot = asyncio.run(utils.fetch_page_content_and_screenshot(url))
                if utils.md5_bytes(screenshot_after) != utils.md5_bytes(new_screenshot):
                    score = utils.compare_images(screenshot_after, new_screenshot)
                    logger.info(f"comparison score {score}")
                    screenshot_before = screenshot_after
                    c.execute(
                        'UPDATE tracked_urls SET content = ?, screenshot_before = ?, screenshot_after = ?, '
                        'changed = 1, last_attempt_successful = 1 WHERE url = ?',
                        (new_content, screenshot_before, new_screenshot, url)
                    )
                else:
                    # If no change, just update 'last_attempt_successful'
                    c.execute('UPDATE tracked_urls SET last_attempt_successful = 1 WHERE url = ?', (url,))
            except Exception as e:
                logger.error(f'Error fetching {url}: {e}')
                c.execute('UPDATE tracked_urls SET last_attempt_successful = 0 WHERE url = ?', (url,))
            c.execute('UPDATE tracked_urls SET last_check_date = ? WHERE url = ?',
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), url))
            logger.info(f'{url} refreshed')
    logger.debug('Updates check completed.')


# Add the job to the scheduler
scheduler.add_job(check_updates, 'interval', minutes=30)


@app.command("/track")
def track(ack, respond, command):
    ack()
    urls = command['text'].replace(',', ' ').split()
    for url in urls:
        if not url:
            continue
        logger.debug(f'Received /track command for URL: {url}')
        try:
            content, screenshot = asyncio.run(utils.fetch_page_content_and_screenshot(url))
            logger.debug('Inserting new tracked URL into database...')
            with DatabaseCursor('trex.db') as c:
                c.execute(
                    'INSERT OR REPLACE INTO tracked_urls '
                    '(url, content, screenshot_after, changed, last_attempt_successful) VALUES (?, ?, ?, 0, 1)',
                    (url, content, screenshot)
                )
            respond(f'Successfully started tracking {url}')
            logger.info(f'Successfully started tracking {url}')
        except Exception as e:
            logger.error(f'Error fetching {url}: {e}')
            respond(f'Failed to fetch {url}, ')


@app.command("/untrack")
def untrack(ack, respond, command):
    ack()
    url = command['text']
    logger.debug(f'Received /untrack command for URL: {url}')
    logger.debug('Deleting URL from database...')
    with DatabaseCursor('trex.db') as c:
        c.execute('DELETE FROM tracked_urls WHERE url = ?', (url,))
    respond(f'Successfully stopped tracking {url}')
    logger.info(f'Successfully stopped tracking {url}')


@app.command("/tracks")
def tracks(ack, respond):
    ack()
    logger.debug('Received /tracks command')
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Tracked URLs",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]
    with DatabaseCursor('trex.db') as c:
        for row in c.execute('SELECT url, changed, last_attempt_successful, last_check_date FROM tracked_urls'):
            url, changed, last_attempt_successful, last_check_date = row
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*URL:*\n{url}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Changed:*\n{'Yes' if changed else 'No'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Last Attempt Successful:*\n{'Yes' if last_attempt_successful else 'No'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Last Check Date:*\n{last_check_date}"
                    }
                ]
            })
            blocks.append({"type": "divider"})

    if len(blocks) == 2:  # Only header and divider were added
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "No tracked URLs found."
            }
        })

    respond({"blocks": blocks})
    logger.info('Listed all tracked URLs in a Slack modal format')


@app.command("/visit")
def visit(ack, respond, command):
    ack()
    urls = command['text'].replace(',', ' ').split()
    for url in urls:
        if not url:
            continue
        logger.debug(f'Received /visit command for URL: {url}')
        logger.debug('Updating URL in database to mark as unchanged...')
        with DatabaseCursor('trex.db') as c:
            c.execute('UPDATE tracked_urls SET changed = 0 WHERE url = ?', (url,))
        respond(f'Visited {url}, marked as unchanged')
        logger.info(f'Visited {url}, marked as unchanged')


@app.command("/show")
def show(ack, respond, command, client):
    ack()
    url = command['text']
    with DatabaseCursor('trex.db') as c:
        c.execute('SELECT screenshot_before, screenshot_after FROM tracked_urls WHERE url = ?', (url,))
        row = c.fetchone()
    if row:
        screenshot_before, screenshot_after = row
        # Assuming utils.upload_to_slack is a function you'll implement to upload files to Slack
        prefix = utils.md5(url)
        if screenshot_before:
            utils.upload_to_slack(client,
                                  command['channel_id'],
                                  screenshot_before,
                                  f'{prefix}-before.png',
                                  "Before Change")
        if screenshot_after:
            utils.upload_to_slack(client,
                                  command['channel_id'],
                                  screenshot_after,
                                  f'{prefix}-after.png',
                                  "After Change")
        if not screenshot_before and not screenshot_after:
            respond(f'No screenshots found for {url}')
    else:
        respond(f'No content found for {url}')


@app.command("/next-run")
def next_job_time(ack, respond):
    ack()
    next_run_time = scheduler.get_jobs()[0].next_run_time
    time_left = next_run_time - datetime.now(pytz.UTC)
    respond(f'The next job is scheduled to run in {utils.format_timedelta(time_left)} '
            f'at: {utils.format_datetime(next_run_time)}')
    logger.info(f'Next job scheduled at: {next_run_time}')


@app.command("/run-now")
def refresh_now(ack, respond):
    ack()
    logger.debug('Received /refresh_now command')
    try:
        check_updates()
        respond('Refresh on all URLs executed successfully.')
        logger.info('Manual refresh executed successfully.')
    except Exception as e:
        logger.error(f'Error during manual refresh: {e}')
        respond(f'Failed to execute manual refresh: {e}')


# Start the Slack app in Socket Mode
if __name__ == "__main__":
    logger.debug('Starting Slack app in Socket Mode...')
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
    logger.debug('Slack app started.')
