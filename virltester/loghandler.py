# -*- coding: utf-8 -*-

import logging
from logging import StreamHandler

# The background is set with 40 plus the number of the color,
# and the foreground with 30.
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


class ColorHandler(StreamHandler):
    """ Add colors to logging output. Partial credits to
    http://opensourcehacker.com/2013/03/14/ultima-python-logger-somewhere-over-the-rainbow/
    """

    def __init__(self, colored):
        super(ColorHandler, self).__init__()
        self.colored = colored

    COLORS = {
        'WARNING': YELLOW,
        'INFO': WHITE,
        'DEBUG': BLUE,
        'CRITICAL': YELLOW,
        'ERROR': RED
    }

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    level_map = {
        logging.DEBUG: (None, CYAN, False),
        logging.INFO: (None, WHITE, False),
        logging.WARNING: (None, YELLOW, True),
        logging.ERROR: (None, RED, True),
        logging.CRITICAL: (RED, WHITE, True),
    }

    def addColor(self, text, bg, fg, bold):
        ctext = ''
        if bg is not None:
            ctext = self.COLOR_SEQ % (40 + bg)
        if bold:
            ctext = ctext + self.BOLD_SEQ
        ctext = ctext + self.COLOR_SEQ % (30 + fg) + text + self.RESET_SEQ
        return ctext

    def colorize(self, record):
        if record.levelno in self.level_map:
            bg, fg, bold = self.level_map[record.levelno]
        else:
            bg, fg, bold = None, WHITE, False

        # exception?
        if record.exc_info:
            formatter = logging.Formatter(format)
            record.exc_text = self.addColor(
                formatter.formatException(record.exc_info), bg, fg, bold)

        record.msg = self.addColor(str(record.msg), bg, fg, bold)
        return record

    def format(self, record):
        if self.colored:
            message = logging.StreamHandler.format(self, self.colorize(record))
        else:
            message = logging.StreamHandler.format(self, record)
        return message
