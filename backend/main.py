"""
main.py — Scheduler entry point.

Starts APScheduler with a configurable interval (default: 60 min for testing,
set CYCLE_INTERVAL_MINUTES=1440 for daily production runs).

Run with:
    python main.py

Or via a systemd service / screen session for persistent operation.
"""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from agent_core import run_all_cycles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


import time

def main():
    interval_minutes = int(os.environ.get("CYCLE_INTERVAL_MINUTES", "60"))
    log.info("DEADMAN.SYS scheduler starting. Cycle interval: %d minute(s).", interval_minutes)

    while True:
        scheduler = BlockingScheduler()
        scheduler.add_job(
            run_all_cycles,
            trigger="interval",
            minutes=interval_minutes,
            id="agent_cycle",
            name="All-agent cycle tick",
            misfire_grace_time=60,    # tolerate up to 1-min late fire
            coalesce=True,            # if multiple fires were missed, run once not many
            max_instances=1,          # never run two ticks simultaneously
        )

        log.info("Scheduler running. First cycle in %d minute(s). Press Ctrl+C to stop.", interval_minutes)
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            log.info("Scheduler stopped by user.")
            break
        except Exception as e:
            log.critical("Scheduler crashed unexpectedly: %s — restarting in 30s.", e, exc_info=True)
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                pass
            time.sleep(30)


if __name__ == "__main__":
    main()

