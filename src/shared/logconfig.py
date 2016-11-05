import colorlog
import logging

# Set the root logger to log all messages. This means that any logger that we
# don't explicitly call setLevel() on will log all messages, allowing the
# handlers to control which logs actually go through.
logging.getLogger().setLevel(logging.DEBUG)

# Code adapted from
#   https://github.com/borntyping/python-colorlog
handler = logging.getLogger().handlers[0]
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s "
    "%(green)s%(module)-10s%(reset)s "
    "%(blue)s%(message)s%(reset)s ",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)

def enableDebugLogging():
    handler.setLevel(logging.DEBUG)

def newLogger(name):
    log = logging.getLogger(name)
    return log
