"""
Logger utility functions for the VerseMind-RAG application
"""
import logging
import os
from dotenv import load_dotenv

# Load environment variables if not already loaded
load_dotenv()

def get_logger_with_env_level(logger_name: str) -> logging.Logger:
    """
    Creates a logger with the level specified in the LOG_LEVEL environment variable.

    Args:
        logger_name: The name of the logger

    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(logger_name)

    # Set log level from environment variable
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()

    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = log_level_map.get(log_level_str, logging.INFO)

    logger.setLevel(log_level)

    return logger
