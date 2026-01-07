"""
Logging configuration for the BRS Consolidator system.
"""
import logging
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure application-wide logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "brs_consolidator.log")
        ]
    )
    
    logger = logging.getLogger("brs_consolidator")
    return logger


# Create default logger
logger = setup_logging()
