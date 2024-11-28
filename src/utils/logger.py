import logging
import os
from functools import wraps


def setup_logger(name="tv_show_renamer"):
    """Configure and return a logger instance with sensitive data filtering."""
    logger = logging.getLogger(name)

    if not logger.handlers:  # Prevent adding handlers multiple times
        logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Set logger to not propagate to root logger
        logger.propagate = False

    return logger


def sanitize_log_message(message: str) -> str:
    """Remove sensitive information from log messages."""
    sensitive_keys = ["api_key", "TMDB_API_KEY", "token", "password"]
    sanitized_message = str(message)

    for key in sensitive_keys:
        if key.upper() in os.environ:
            sanitized_message = sanitized_message.replace(
                os.environ[key.upper()], f"[{key.upper()}_HIDDEN]"
            )

    return sanitized_message


def log_safely(func):
    """Decorator to ensure all logging calls are sanitized."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = setup_logger()
            logger.error(sanitize_log_message(str(e)))
            raise

    return wrapper


def format_show_name(name: str) -> str:
    """Format show name with consistent casing."""
    # Title case for the main text, preserving specific capitalizations
    words = name.strip().split()
    formatted_words = []

    # Words that should be lowercase unless at start
    articles = {"a", "an", "the", "in", "on", "at", "for", "to", "of", "with", "by"}

    for i, word in enumerate(words):
        # First word or not an article: capitalize
        if i == 0 or word.lower() not in articles:
            formatted_words.append(word.title())
        else:
            formatted_words.append(word.lower())

    return " ".join(formatted_words)
