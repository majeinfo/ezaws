import logging
from datetime import datetime

def log_error(msg):
    log(logging.ERROR,msg)

def log_info(msg):
    log(logging.INFO,msg)

def log_debug(msg):
    log(logging.DEBUG,msg)

def log(level,msg):
    logger = logging.getLogger('general')
    logger.log(level,msg)


def log_time(msg):
    log_info("[%s] %s" % (msg, datetime.now()))