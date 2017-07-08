import colorlog
import logging
import os

# Set the root logger to log all messages. This means that any logger that we
# don't explicitly call setLevel() on will log all messages, allowing the
# handlers to control which logs actually go through.
logging.getLogger().setLevel(logging.DEBUG)

MAX_NAME_LENGTH = 11

# Code adapted from
#   https://github.com/borntyping/python-colorlog
# Pylint thinks these are constants, but they're not. Disable invalid-name on
# them.
handler = logging.getLogger().handlers[0]  # pylint: disable=invalid-name
formatter = colorlog.ColoredFormatter(  # pylint: disable=invalid-name
    "%(log_color)s%(levelname)-8s%(reset)s "
    "%(green)s%(name)-{maxnamelen}s%(reset)s "
    "%(blue)s%(message)s%(reset)s ".format(maxnamelen = MAX_NAME_LENGTH),
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

# String to use to replace the middle part of a long module name.
SHORTENED_MIDDLE = "..."

def newLogger(fullname):
    # Empirically __name__'s are dot-separated in these modules, not
    # slash-separated. We could do an os.basename to deal with the case where
    # they're slash-separated, but if that happens then the rpartition below is
    # probably wrong. I don't want to write the logic to handle this case until
    # we've actually seen it happen so we can test it, so for now just assert
    # if we see any slashes.
    assert os.sep not in fullname

    # The logic below does weird things if there isn't room for at least one
    # character on each side of the "..." in the middle when names are
    # shortened. I'm sure we could handle that, but it shouldn't happen, so
    # let's just assert.
    assert MAX_NAME_LENGTH >= len(SHORTENED_MIDDLE) + 2

    # Ignore everything before the last dot.
    _, _, name = fullname.rpartition(".")

    # Make sure the names don't get too long.
    if len(name) > MAX_NAME_LENGTH:
        # Note: don't just use endLen for both beginning and end, because
        # that's wrong if MAX_NAME_LENGTH - len(middle) is odd. Round down for
        # endLen so that if we decide to set MAX_NAME_LENGTH to an even number,
        # then the odd character will be used for the start of the module name,
        # which I think is probably more useful than the end.
        middle   = SHORTENED_MIDDLE
        endLen   = (MAX_NAME_LENGTH - len(middle)) / 2
        end      = name[-endLen:]
        beginLen = MAX_NAME_LENGTH - endLen - len(middle)
        begin    = name[:beginLen]

        name = begin + middle + end

    log = logging.getLogger(name)
    return log
