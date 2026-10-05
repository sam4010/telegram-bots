import os
import sys
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from downloader_bot import main as run_downloader_bot
from jobs_scraper_bot import post_jobs_batch

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("CloudMaster")

# Minimal HTTP Health Check Server (Keeps Render.com Free Tier 24/7 Alive)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"DataSnap Bot System is LIVE 24/7")

    def log_message(self, format, *args):
        pass  # Suppress health check spam in logs

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server listening on port {port} for 24/7 cloud pinging...")
    server.serve_forever()

# Background Job Posting Scheduler (Runs every 3 hours)
def run_job_scheduler():
    interval = 3 * 3600  # 3 hours
    logger.info("Background Job Scheduler initialized.")
    while True:
        try:
            logger.info("Executing scheduled remote jobs fetch...")
            posted = post_jobs_batch(count=2)
            logger.info(f"Published {posted} new jobs to @remotetechjobs_hub.")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    logger.info("=== Starting DataSnap 24/7 Unified Cloud Master ===")

    # 1. Start HTTP Health Server in a daemon thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # 2. Start 3-Hour Job Posting Scheduler in a daemon thread
    scheduler_thread = threading.Thread(target=run_job_scheduler, daemon=True)
    scheduler_thread.start()

    # 3. Run the Video Downloader Bot in the main thread
    logger.info("Starting Telegram Video Downloader Bot...")
    run_downloader_bot()
