import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clean default handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # JSON Log Formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d'
    )
    
    # Stderr stream handler
    log_handler = logging.StreamHandler(sys.stderr)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    
    # Disable default uvicorn access logging format, let it use standard logging
    logging.getLogger("uvicorn.access").handlers = logger.handlers
    logging.getLogger("uvicorn.error").handlers = logger.handlers

setup_logging()
logger = logging.getLogger("namma_bus")
