import math

# Normal delimiter; separates tokens in messages.
TOKEN_DELIM  = " "

# Used to indicate the start of an unbounded string; must be the first
# character after TOKEN_DELIM.
START_STRING = "|"

def tokenize(message):
    tokens  = []
    isFirst = True
    while message:
        if message.startswith(START_STRING):
            if isFirst:
                raise InvalidMessageError("Message starts with unbounded " \
                                          "string.")
            tok  = message[len(START_STRING):]
            rest = ""
        else:
            tok, _, rest = message.partition(TOKEN_DELIM)
        tokens.append(tok)
        message = rest

    if not tokens:
        raise InvalidMessageError("Empty message.")

    return (tokens[0], tokens[1:])

class InvalidMessageError(StandardError):
    def __init__(self, badMessage, errorDesc):
        self.badMessage = badMessage
        self.errorDesc  = errorDesc

    def __str__(self):
        return "{desc}  (Message is: {msg!r})".format(desc = self.errorDesc,
                                                      msg  = self.badMessage)


def parsePos(descs):
    if len(descs) != 2:
        raise ValueError("Position {0!r} has wrong length (expected 2)." \
            .format(descs))
    return map(parseFloat, descs)

def parseFloat(desc):
    val = float(desc)
    if not isfinite(val):
        raise ValueError("Floating-point value {0!r} ({1!r}) is not finite." \
            .format(desc, val))
    return val

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)

