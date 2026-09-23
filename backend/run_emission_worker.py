"""run_emission_worker.py — Worker durable para emisión fiscal."""
import sys

from config import settings
from logging_utils import configure_logging
from services.emission_queue_service import run_worker_loop

if __name__ == "__main__":
    configure_logging(level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
    try:
        run_worker_loop()
    except KeyboardInterrupt:
        sys.exit(0)

