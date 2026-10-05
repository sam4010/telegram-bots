import time
import logging
from jobs_scraper_bot import post_jobs_batch

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("AutoScheduler")

# Interval in seconds between job batches (every 3 hours)
INTERVAL_SECONDS = 3 * 3600

def run_scheduler():
    logger.info("Starting automated job posting scheduler (every 3 hours)...")
    while True:
        try:
            logger.info("Posting scheduled batch of fresh remote jobs...")
            posted = post_jobs_batch(count=2)
            logger.info(f"Published {posted} jobs to @remotetechjobs_hub.")
        except Exception as e:
            logger.error(f"Scheduler encountered error: {e}")

        logger.info(f"Sleeping for {INTERVAL_SECONDS / 3600:.1f} hours until next batch...")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_scheduler()
