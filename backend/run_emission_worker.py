"""run_emission_worker.py — Worker durable para emisión fiscal."""
import sys

from services.emission_queue_service import run_worker_loop

if __name__ == "__main__":
    try:
        run_worker_loop()
    except KeyboardInterrupt:
        sys.exit(0)

