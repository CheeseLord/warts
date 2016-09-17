from collections import namedtuple
import math

# Normal delimiter; separates tokens in messages.
TOKEN_DELIM  = " "

# Used to indicate the start of an unsafe string; must be the first character
# after TOKEN_DELIM.
START_STRING = "|"


# Mapping from command word to Message (sub)classes.
messagesByCommand = {}


class Message(object):
    command = None

    # Note: this doesn't seem to be necessary, but that might just be because
    # (I think) namedtuple overrides __new__ instead of __init__.
    # def __init__(self, *args):
    #     super(Message, self).__init__(*args)

    # @classmethod
    # def setCommandWord(cls, word):
    #     assert cls.command is None
    #     cls.command = word
    #     # TODO: Register command word in some global mapping, used when
    #     # deserializing methods.

    def serialize(self):
        return buildMessage(self.command, self.encodeArgs())

    # TODO: I don't think this is actually used; maybe remove it or comment it
    # out?
    @classmethod
    def deserialize(cls, data):
        cmd, args = tokenize(data)
        assert cmd == cls.command
        return cls.decodeArgs(args)

    def encodeArgs(self):
        raise NotImplementedError

    @classmethod
    def decodeArgs(cls, args):
        raise NotImplementedError

class ArgumentSpecification:
    """
    Class used to describe how one logical argument to a message is encoded and
    decoded. Note that a single logical argument might be encoded as several
    (space-separated) words in the actual message string -- for example, a
    position is encoded as two words, one for each coordinate.
    """

    def __init__(self, numWords, decodeFunc, encodeFunc=None):
        """
        Initialize an ArgumentSpecification.
          - numWords is the number of words used to encode this argument in a
            message string.
          - decodeFunc is a function to parse those words into a more useful
            object. It takes in a tuple of strings if numWords > 1, else a
            single string, and returns a parsed object.
          - encodeFunc is similar, but operates in reverse. It returns a tuple
            of strings if numWords > 1, else a single string. If numWords == 1,
            then encodeFunc may be omitted, in which case the argument will
            just be str()ed.
        """

        self.count      = numWords
        self.decodeFunc = decodeFunc

        if encodeFunc is None:
            assert numWords == 1
            # TODO: Should we use repr instead?
            self.encodeFunc = str
        else:
            self.encodeFunc = encodeFunc

    def encode(self, arg):
        words = self.encodeFunc(arg)
        assert len(words) == self.count
        return words

    def decode(self, words):
        assert type(words) == list and len(words) == self.count
        if self.count == 1:
            (word,) = words
            return self.decodeFunc(word)
        else:
            return self.decodeFunc(tuple(words))

def defineMessageType(commandWord, argSpecs):
    """
    Define a new message type.

    argSpecs should be a list of tuples (name, spec), where name is the name
    of that argument and spec is an ArgumentSpecification object describing
    how it is encoded and decoded when the message is serialized and
    deserialized.
    """

    if commandWord in messagesByCommand:
        raise ValueError("Message command {0!r} is already taken."
                         .format(commandWord))

    # TODO: snake_case to BigCamelCase?
    # Ideally we'd choose this name so that it matches the actual message class
    # name. Or just override __str__ in Message.
    NamedTupleType = namedtuple(commandWord + "_message_tuple",
                                [spec[0] for spec in argSpecs])

    # Subclass from Message before NamedTupleType, so that we can override some
    # methods of NamedTupleType in Message. (We may want to do this with
    # __str__?)
    class NewMessageType(Message, NamedTupleType):
        command = commandWord

        def __init__(self, *args):
            super(NewMessageType, self).__init__(*args)

        def encodeArgs(self):
            args = []
            # Yay, closures!
            assert len(self) == len(argSpecs)
            for val, (name, spec) in zip(self, argSpecs):
                args.extend(spec.encode(val))
            return args

        @classmethod
        def decodeArgs(cls, args):
            # TODO: Error checking
            initArgs = []
            i = 0
            while i < len(argSpecs):
                spec = argSpecs[i][1]
                initArgs.append(spec.decode(args[:spec.count]))
                args = args[spec.count:]
                i += 1
            return cls(*initArgs)

    messagesByCommand[commandWord] = NewMessageType
    return NewMessageType

def deserializeMessage(data):
    cmd, args = tokenize(data)
    if cmd not in messagesByCommand:
        raise InvalidMessageError(data, "Unrecognized message command.")

    messageType = messagesByCommand[cmd]

    # It would seem logical to call messageType.deserialize here, but that's
    # somewhat wasteful since it takes the original string and therefore has to
    # tokenize the message again. Instead, call decodeArgs (which does the real
    # work) directly.
    return messageType.decodeArgs(args)


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

def invalidCommand(message):
    raise InvalidMessageError(message.serialize(),
        "Unrecognized command '{command}'.".format(command=message.command))

# def checkArity(command, args, expectedLen):
#     if len(args) != expectedLen:
#         # Yes, this is some redundant work, but it only happens when there's a
#         # bug.
#         message = buildMessage(command, args)
#         raise InvalidMessageError(message,
#             "Incorrect number of arguments for message; got {got}, expected "
#             "{expect}.".format(got=len(args), expect=expectedLen))

# def invalidCommand(command, args):
#     message = buildMessage(command, args)
#     raise InvalidMessageError(message,
#         "Unrecognized command '{command}'.".format(command=command))


class InvalidMessageError(StandardError):
    def __init__(self, badMessage, errorDesc):
        self.badMessage = badMessage
        self.errorDesc  = errorDesc

    def __str__(self):
        return "{desc}  (Message is: {msg!r})".format(desc = self.errorDesc,
                                                      msg  = self.badMessage)


def encodePos(pos):
    return map(str, pos)

def parsePos(descs):
    if len(descs) != 2:
        raise ValueError("Position {0!r} has wrong length (expected 2)." \
            .format(descs))
    return tuple(map(parseFloat, descs))

def parseFloat(desc):
    val = float(desc)
    if not isfinite(val):
        raise ValueError("Floating-point value {0!r} ({1!r}) is not finite." \
            .format(desc, val))
    return val

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)
