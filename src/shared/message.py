import math

# Normal delimiter; separates tokens in messages.
TOKEN_DELIM  = " "

# Used to indicate the start of an unsafe string; must be the first character
# after TOKEN_DELIM.
START_STRING = "|"

# TODO: We can and should unit-test tokenize and buildMessage.
# For an arbitrary string command and an arbitrary list of strings args,
#     tokenize(buildMessage(command, args, lastIsUnsafe=<whatever>))
# should either return exactly (command, args) or raise an InvalidMessageError.
#
# Note: this isn't quite true. buildMessage('', ['']) gives ' ' (one space),
# but tokenize(' ') returns ('', []), not ('', ['']). This is maybe a bug in
# tokenize, but really the solution is probably not to allow the empty string
# as a command or argument.

def tokenize(message):
    tokens  = []
    isFirst = True
    while message:
        if message.startswith(START_STRING):
            if isFirst:
                raise InvalidMessageError(message,
                                          "Message starts with unsafe string.")
            tok  = message[len(START_STRING):]
            rest = ""
        else:
            tok, _, rest = message.partition(TOKEN_DELIM)
        tokens.append(tok)
        message = rest
        isFirst = False

    if not tokens:
        raise InvalidMessageError(message, "Empty message.")

    return (tokens[0], tokens[1:])

def buildMessage(command, args, lastIsUnsafe=False):
    """
    Build a message from the given command and arguments. The arguments don't
    have to be strings; if they aren't, then they will be str()ed.
    If lastIsUnsafe, then the last argument is a potentially unsafe string (for
    example, something typed by the user) and will be specially delimited.
    Only the last argument is allowed to be unsafe.
    """

    command = str(command)
    args    = map(str, args)
    lastArg = None

    if lastIsUnsafe:
        if not args:
            raise InvalidMessageError(command, "No arguments.")
        lastArg = args[-1]
        args = args[:-1]

    # Build the message. This has to come before the checking so that we have a
    # message to pass to any InvalidMessageErrors that we raise. Note that if
    # we raise an InvalidMessageError, the message we report with it isn't
    # actually a real message, because in that situation we've failed to build
    # a message. But it doesn't seem worth it to create yet another Exception
    # subclass, and InvalidMessageError seems more or less logically correct
    # for that type of error.
    message = TOKEN_DELIM.join([command] + args)
    if lastIsUnsafe:
        message += TOKEN_DELIM + START_STRING + lastArg

    # Check that (with the exception of the possible unsafe string at the end),
    # the message tokenizes correctly.

    def checkToken(token, tokenDesc):
        if TOKEN_DELIM in token:
            raise InvalidMessageError(message, "{0} may not contain {1!r}"
                                               .format(tokenDesc, TOKEN_DELIM))
        if command.startswith(START_STRING):
            raise InvalidMessageError(message, "{0} may not start with {0!r}"
                                               .format(tokenDesc,
                                                       START_STRING))

    checkToken(command, "Command")
    for arg in args:
        checkToken(arg, "Argument")

    # Checks passed; this is a valid message.
    return message

def checkArity(command, args, expectedLen):
    if len(args) != expectedLen:
        # Yes, this is some redundant work, but it only happens when there's a
        # bug.
        message = buildMessage(command, args)
        raise InvalidMessageError(message,
            "Incorrect number of arguments for message; got {got}, expected "
            "{expect}.".format(got=len(args), expect=expectedLen))

def invalidCommand(command, args):
    message = buildMessage(command, args)
    raise InvalidMessageError(message,
        "Unrecognized command '{command}'.".format(command=command))


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

