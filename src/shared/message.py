from collections import namedtuple
import math

# Normal delimiter; separates tokens in messages.
TOKEN_DELIM  = " "

# Used to indicate the start of an unsafe string; must be the first character
# after TOKEN_DELIM.
START_STRING = "|"


class Message(object):
    command = None

    def __init__(self, *args):
        # TODO: Is this the right magic line to put here? Or can we use
        # self.__class__ instead of Message? (That seems to cause infinite
        # recursion, so probably not....) Or can we just use super() with no
        # args? How does multiple inheritance actually work with new-style
        # classes?
        super(Message, self).__init__(*args)

    # @classmethod
    # def setCommandWord(cls, word):
    #     assert cls.command is None
    #     cls.command = word
    #     # TODO: Register command word in some global mapping, used when
    #     # deserializing methods.

    def serialize(self):
        return buildMessage(self.command, self.getArgs())

    @classmethod
    def deserialize(cls, data):
        cmd, args = tokenize(data)
        assert cmd == cls.command
        return cls.fromArgs(args)

    def getArgs(self):
        raise NotImplementedError

    @classmethod
    def fromArgs(cls, args):
        raise NotImplementedError

# TODO: Provide a way to specify a function to parse each argument. For
# example, an id needs to be parsed using something like
#     int
# and a position using something like
#     lambda desc: tuple(map(float, desc))

def defineMessageType(commandWord, argSpec):
    """
    Define a new message type.

    argSpec should be a list of tuples (name, count), where name is the name
    of that argument and count is the number of values used to encode it when
    the message is serialized. Where count > 1, the attribute corresponding to
    the argument will be a tuple.
    """

    NamedTupleType = namedtuple(commandWord + "_message_tuple",
                                [spec[0] for spec in argSpec])

    # TODO: Which order should the superclasses be listed?
    # I think we want Message to win where there's a conflict, so it goes
    # first? Right? Is that how this works?
    class NewMessageType(Message, NamedTupleType):
        command = commandWord

        def __init__(self, *args):
            super(NewMessageType, self).__init__(*args)

        def getArgs(self):
            args = []
            # Yay, closures!
            assert len(self) == len(argSpec)
            for val, (name, count) in zip(self, argSpec):
                if count == 1:
                    args.append(val)
                elif count > 1:
                    args.extend(list(val))
                else:
                    raise ValueError("Count must be at least 1")
            return args

        @classmethod
        def fromArgs(cls, args):
            # TODO: Error checking
            initargs = []
            i = 0
            while i < len(argSpec):
                count = argSpec[i][1]
                if count == 1:
                    initargs.append(args[0])
                else:
                    initargs.append(tuple(args[:count]))
                args = args[count:]
                i += 1
            return cls(*initargs)

    # TODO: Register command word

    return NewMessageType

NewObeliskMessage = defineMessageType("new_obelisk", [("playerId", 1),
                                                      ("pos",      2)])

# class NewObeliskMessage(Message):
#     __class__.setCommandWord("new_obelisk")
#
#     def __init__(self, playerId, pos):
#         self.playerId = playerId
#         self.pos      = pos
#
#     def getArgs(self):
#         x, y = self.pos
#         return [self.playerId, x, y]
#
#     @classmethod
#     def fromArgs(cls, args):
#         playerId, x, y = args
#         return cls(playerId, (x, y))


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
