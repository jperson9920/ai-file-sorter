"""Logging configuration and setup."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict


def setup_logger(config: Dict) -> logging.Logger:
    """Initialize logging with file and console handlers.

    Args:
        config: Configuration dictionary with 'logging' section

    Returns:
        Configured root logger
    """
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/image_tagger.log')

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # File handler with rotation
    max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
    backup_count = log_config.get('backup_count', 5)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    # Console handler (if enabled)
    if log_config.get('console_output', True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

    logger.info("="*60)
    logger.info("Image Tagging System - Session Start")
    logger.info("="*60)
    logger.info(f"Log level: {log_config.get('level', 'INFO')}")
    logger.info(f"Log file: {log_file}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
