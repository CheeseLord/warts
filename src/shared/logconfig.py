import colorlog
import logging

# Code adapted from
#   https://github.com/borntyping/python-colorlog
handler = logging.getLogger().handlers[0]
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(green)s"
    "%(module)-10s%(reset)s %(blue)s%(message)s",
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

def newLogger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    return log
