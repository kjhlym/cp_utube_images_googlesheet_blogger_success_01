import sys
import traceback
from functools import wraps
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_exceptions(func):
    """Decorator to handle exceptions in functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    return wrapper

class RequestError(Exception):
    """Custom exception for request errors"""
    pass

class APIError(Exception):
    """Custom exception for API errors"""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def log_error(error_msg):
    """Log error message"""
    logger.error(error_msg)

def log_warning(warning_msg):
    """Log warning message"""
    logger.warning(warning_msg)

def log_info(info_msg):
    """Log info message"""
    logger.info(info_msg)

__all__ = [
    'handle_exceptions',
    'RequestError',
    'APIError',
    'ValidationError',
    'log_error',
    'log_warning',
    'log_info'
] 