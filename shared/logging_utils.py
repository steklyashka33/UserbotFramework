import logging
import sys

def setup_logger(name: str):
    """Setup a unified log format for all MVP modules."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid log duplication if logger is already set up
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Format: [Time] [LEVEL] [Name] Message
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# Create a global logger for shared needs
logger = setup_logger("MVP")
