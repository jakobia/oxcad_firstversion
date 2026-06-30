"""
logger.py - Logging utility for CAD app

Configures application-wide logging.
"""

import logging
from typing import Optional

def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Set up logging for the application.
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        filename=log_file,
        filemode="a"
    )
    if not log_file:
        # Also log to console
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(console)
