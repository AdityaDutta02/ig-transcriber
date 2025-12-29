"""
Logging Configuration Module

Sets up structured logging for the application using loguru.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from config import LoggingConfig


def setup_logger(config: LoggingConfig) -> logger:
    """
    Set up application logger with configured settings.
    
    Args:
        config: LoggingConfig object with logging settings
        
    Returns:
        Configured logger instance
    """
    # Remove default logger
    logger.remove()
    
    # Add console handler if enabled
    if config.console:
        logger.add(
            sys.stdout,
            format=config.format,
            level=config.level,
            colorize=True,
        )
    
    # Ensure log directory exists
    log_file = Path(config.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Add file handler
    logger.add(
        config.file,
        format=config.format,
        level=config.level,
        rotation=config.max_file_size,
        retention=config.backup_count,
        compression="zip",
    )
    
    # Add separate error file handler
    error_file = Path(config.error_file)
    error_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        config.error_file,
        format=config.format,
        level="ERROR",
        rotation=config.max_file_size,
        retention=config.backup_count,
        compression="zip",
    )
    
    logger.info("Logger initialized")
    logger.debug(f"Log level: {config.level}")
    logger.debug(f"Console logging: {config.console}")
    logger.debug(f"File logging: {config.file}")
    
    return logger


# Stub for future implementation
if __name__ == "__main__":
    # Test logger setup
    from config import load_config
    
    config = load_config()
    test_logger = setup_logger(config.logging)
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
