# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
from datetime import datetime

from sunbeam_migrate import config

CONFIG = config.get_config()


def configure_logging(debug: bool = False):
    """Configure logging based on the user configuration."""
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.getLevelName(CONFIG.log_level.upper())

    logger = logging.getLogger()
    logger.setLevel(log_level)

    if CONFIG.log_console:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        log_fmt = logging.Formatter(
            "%(asctime)s,%(msecs)03d %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream_handler.setFormatter(log_fmt)
        logger.addHandler(stream_handler)

    if CONFIG.log_dir:
        CONFIG.log_dir.mkdir(mode=0o750, exist_ok=True)

        log_fname = f"sunbeam-migrate-{datetime.now():%Y%m%d-%H%M%S.%f}.log"
        log_path = CONFIG.log_dir / log_fname

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        log_fmt = logging.Formatter(
            "%(asctime)s,%(msecs)d %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )
        file_handler.setFormatter(log_fmt)
        logger.addHandler(file_handler)
