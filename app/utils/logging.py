import logging

def get_logger(name: str = "uvicorn.error") -> logging.Logger:
    return logging.getLogger(name)
