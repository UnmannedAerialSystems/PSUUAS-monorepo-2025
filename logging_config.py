import logging
import colorlog
from datetime import datetime
import os

def configure_logging():
    # Ensure the flight_logs directory exists
    os.makedirs("./flight_logs", exist_ok=True)

    # Create a log file with a timestamp
    log_filename = f"./flight_logs/log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    # Get the logger
    logger = logging.getLogger()

    # Check if the logger already has handlers to avoid duplicates
    if not logger.handlers:
        # Configure the file handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s\t- %(message)s'))

        # Configure the console handler with colors
        console_handler = colorlog.StreamHandler()
        console_handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        ))

        # Add handlers to the logger
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger