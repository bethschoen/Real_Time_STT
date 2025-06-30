import logging
from logging.handlers import RotatingFileHandler
import os
from flask import session, has_request_context

class SessionIDFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.session_id = session.get('session_id', 'N/A')
        else:
            record.session_id = 'N/A'
        return True

# Ensure the logs directory exists
if not os.path.exists('app/logs'):
    os.makedirs('app/logs')

# Configure the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a RotatingFileHandler - save to log files that will delete once they reach a certain size and number of files
handler = RotatingFileHandler(
    # each file is 1MB
    # keep the last 3 files
    "app/logs/rts_app_log.log", maxBytes=1024*1024, backupCount=3
)

# Create a StreamHandler - display logs in the terminal
stream_handler = logging.StreamHandler()

# Create a logging format that includes session ID
formatter = logging.Formatter('Datetime %(asctime)s - Level %(levelname)s - Session ID %(session_id)s: - %(message)s')
handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)
logger.addHandler(stream_handler)

# Add the custom filter to the logger
session_filter = SessionIDFilter()
logger.addFilter(session_filter)