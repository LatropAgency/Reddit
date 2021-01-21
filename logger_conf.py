import logging
import sys
from logging import handlers

LOGMODES = {
    'ALL': (logging.DEBUG, logging.INFO, logging.ERROR, logging.WARNING, logging.CRITICAL, logging.NOTSET),
    'ERROR': (logging.ERROR,),
    'WARNING': (logging.WARNING,),
    'DISABLE': (),
}


class StdoutFilter(logging.Filter):
    def __init__(self, logmode):
        self.logmode = logmode

    def filter(self, record):
        return record.levelno in self.logmode


def configurate_logger(logmode):
    format = '%(asctime)s - %(levelname)s - %(message)s'
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    format = logging.Formatter(format)

    ch = logging.StreamHandler(sys.stdout)
    ch.addFilter(StdoutFilter(LOGMODES[logmode]))
    ch.setFormatter(format)
    log.addHandler(ch)

    fh = handlers.RotatingFileHandler('app.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(format)
    log.addHandler(fh)
