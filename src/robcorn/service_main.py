from __future__ import annotations

import time

from .config import db_path
from .repository import Repository
from .scheduler import SchedulerEngine


def main() -> None:
    repository = Repository(db_path())
    repository.init()
    scheduler = SchedulerEngine(db_path())
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
