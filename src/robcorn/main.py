from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import logs_dir
from .service_main import main as service_main
from .ui.main_window import run


def _configure_logging() -> None:
    logs_dir().mkdir(parents=True, exist_ok=True)
    log_path = logs_dir() / "robcorn.log"
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])


if __name__ == "__main__":
    _configure_logging()
    if "--service" in sys.argv:
        service_main()
    else:
        run()
