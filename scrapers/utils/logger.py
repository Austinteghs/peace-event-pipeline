"""
Logging utilities for scrapers
"""

import logging
import os

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger('scrapers.utils')

# Troubleshooting mode
TROUBLESHOOTING = os.environ.get("TROUBLESHOOTING", "false").lower() == "true"


def log_if_troubleshooting(message):
    """Log message only if troubleshooting mode is enabled"""
    if TROUBLESHOOTING:
        logger.info(f"[TROUBLESHOOT] {message}")