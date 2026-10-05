import sys
import requests
import time
import logging

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BOT_TOKEN = "8815293724:AAH-oOJUKI0yy7aUfyxfBBdU-aY86-uSkZw"
TARGET_CHANNEL = "@remotetechjobs_hub"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

posted_jobs_cache = set()

def fetch_remote_tech_jobs():
    """Fetch high-paying remote tech jobs from RemoteOK open API"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    url = "https://remoteok.com/api"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            jobs = [j for j in data[1:] if isinstance(j, dict) and j.get('position')]
            return jobs
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
    return []

def format_job_card(job):
    """Format job details into a high-converting Telegram card"""
    title = job.get('position', 'Software Engineer')
    company = job.get('company', 'Tech Company')
    location = job.get('location', 'Remote (Worldwide)')
    salary = job.get('salary', 'Competitive')
    url = job.get('url', 'https://remoteok.com')
    tags = job.get('tags', [])[:4]
    tag_str = " ".join([f"#{t.replace(' ', '').replace('-', '_')}" for t in tags])

    card = (
        f"💼 *{title}*\n"
        f"🏢 *Company:* {company}\n"
        f"📍 *Location:* {location}\n"
        f"💰 *Compensation:* {salary}\n\n"
        f"🏷️ {tag_str}\n\n"
        f"🔗 [Apply Directly Here]({url})\n\n"
        f"⚡ _Shared by @datasnap_downloader_bot • 100% Verified Remote_"
    )
    return card

def send_telegram_message(bot_token, chat_id, text):
    """Send formatted markdown post to Telegram channel"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': False
    }
    res = requests.post(url, json=payload, timeout=10)
    return res.json()

def post_jobs_batch(count=3):
    """Post a batch of fresh jobs to the channel"""
    jobs = fetch_remote_tech_jobs()
    posted = 0
    for job in jobs:
        job_id = job.get('id') or job.get('url')
        if job_id not in posted_jobs_cache:
            card_text = format_job_card(job)
            res = send_telegram_message(BOT_TOKEN, TARGET_CHANNEL, card_text)
            if res.get('ok'):
                posted_jobs_cache.add(job_id)
                posted += 1
                logger.info(f"Posted job: {job.get('position')} at {job.get('company')}")
                time.sleep(2)  # Delay between posts
            else:
                logger.error(f"Failed to post: {res}")
            if posted >= count:
                break
    return posted

if __name__ == "__main__":
    print(f"Posting initial {3} jobs to {TARGET_CHANNEL}...")
    n = post_jobs_batch(3)
    print(f"Successfully published {n} jobs to {TARGET_CHANNEL}!")
