import logging

def log_error(msg):
    log(logging.ERROR,msg)

def log_info(msg):
    log(logging.INFO,msg)

def log_debug(msg):
    log(logging.DEBUG,msg)

def log(level,msg):
    logger = logging.getLogger('ezaws')
    logger.log(level,msg)
