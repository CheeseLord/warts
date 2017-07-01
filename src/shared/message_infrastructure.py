from collections import namedtuple
import sys
import traceback

from logconfig import newLogger

log = newLogger(__name__)


# Normal delimiter; separates tokens in messages.
TOKEN_DELIM  = " "

# Used to indicate the start of an unsafe string; must be the first character
# after TOKEN_DELIM.
START_STRING = "|"


# Mapping from command word to Message (sub)classes.
messagesByCommand = {}


def defineMessageType(commandWord, argNamesAndSpecs):
    """
    Define a new message type.

    argNamesAndSpecs should be a list of tuples (name, spec), where name is the
    name of that argument and spec is an ArgumentSpecification object
    describing how it is encoded and decoded when the message is serialized and
    deserialized.
    """

    if commandWord in messagesByCommand:
        raise ValueError("Message command {0!r} is already taken."
                         .format(commandWord))
    assert not any(nameSpec[1].unsafe for nameSpec in argNamesAndSpecs[:-1])

    # TODO: snake_case to BigCamelCase?
    # Ideally we'd choose this name so that it matches the actual message class
    # name. Or just override __str__ in Message.
    NamedTupleType = namedtuple(commandWord + "_message_tuple",
                                [nameSpec[0] for nameSpec in argNamesAndSpecs])

    # Subclass from Message before NamedTupleType, so that we can override some
    # methods of NamedTupleType in Message. (We may want to do this with
    # __str__?)
    class NewMessageType(Message, NamedTupleType):
        command  = commandWord
        argSpecs = [nameSpec[1] for nameSpec in argNamesAndSpecs]

        def __init__(self, *args):
            super(NewMessageType, self).__init__(*args)

    messagesByCommand[commandWord] = NewMessageType
    return NewMessageType

def serializeMessage(message):
    argStrings = []
    assert len(message.argSpecs) == len(message)
    for argSpec, arg in zip(message.argSpecs, message):
        argWords = argSpec.encode(arg)
        if argSpec.count == 1:
            argWords = (argWords,)
        argStrings.extend(argWords)
    lastIsUnsafe = message.argSpecs[-1].unsafe if message.argSpecs else False
    return buildMessage(message.command, argStrings, lastIsUnsafe=lastIsUnsafe)

# Note: errorOnFail might never be passed as False; currently all callers that
# don't want to crash still pass errorOnFail=True and just handle
# InvalidMessageError themselves.
def deserializeMessage(data, errorOnFail=True):
    try:
        cmd, argStrings = tokenize(data)
        if cmd not in messagesByCommand:
            raise InvalidMessageError(data, "Unrecognized message command.")

        messageType = messagesByCommand[cmd]

        args = []
        for argSpec in messageType.argSpecs:
            if argSpec.count > len(argStrings):
                raise InvalidMessageError(data,
                                          "Not enough arguments for command.")
            if argSpec.count == 1:
                args.append(argSpec.decode(argStrings[0]))
            else:
                currWords = tuple(argStrings[:argSpec.count])
                args.append(argSpec.decode(currWords))
            argStrings = argStrings[argSpec.count:]

        if len(argStrings) > 0:
            raise InvalidMessageError(data, "Too many arguments for command.")

        return messageType(*args)
    except StandardError, exc:
        # Log the full traceback, noting where we are, much like what Twisted
        # does for an uncaught exception.
        stackBelow = traceback.format_exception(sys.exc_type, sys.exc_value,
                                                sys.exc_traceback)
        stackAbove = traceback.format_stack()
        # Remove the last stack entry from stackAbove, because that's the call
        # to format_stack() which isn't part of the exception's traceback.
        stackAbove = stackAbove[:-1]
        # Remove the first entry from stackBelow, because that's the "Traceback
        # (most recent call last)" line which we want at the top of the
        # traceback, rather than the middle.
        headerLine = stackBelow[0]
        stackBelow = stackBelow[1:]
        # Add an extra entry in the middle noting that this is where we caught
        # the exception.
        midLine = "--- <exception caught here> ---\n"
        fullStack = [headerLine] + stackAbove + [midLine] + stackBelow
        log.debug("Caught exception in deserializeMessage.\n" +
                  "".join(fullStack))

        if errorOnFail:
            # Reraise the exception, but converted (if necessary) to an
            # InvalidMessageError. This ensures that it'll be handled correctly
            # by the caller and not cause the program to crash unnecessarily.
            if isinstance(exc, InvalidMessageError):
                raise exc
            else:
                raise InvalidMessageError(data, str(exc))
        else:
            return None

class Message(object):
    command  = None
    argSpecs = None

    # Note: this doesn't seem to be necessary, but that might just be because
    # (I think) namedtuple overrides __new__ instead of __init__.
    # def __init__(self, *args):
    #     super(Message, self).__init__(*args)

    # For a message that was just deserialized, maybe we should cache the
    # original string and return it, rather than regenerating it?
    def serialize(self):
        return serializeMessage(self)

    def __str__(self):
        return self.serialize()

class ArgumentSpecification:
    """
    Class used to describe how one logical argument to a message is encoded and
    decoded. Note that a single logical argument might be encoded as several
    (space-separated) words in the actual message string -- for example, a
    position is encoded as two words, one for each coordinate.
    """

    def __init__(self, numWords, decodeFunc, encodeFunc=None, unsafe=False):
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
          - unsafe indicates whether the last word of this argument is an
            unsafe string.
        """

        self.count      = numWords
        self.decodeFunc = decodeFunc

        if encodeFunc is None:
            assert numWords == 1
            # TODO: Should we use repr instead?
            self.encodeFunc = str
        else:
            self.encodeFunc = encodeFunc

        self.unsafe = unsafe

    def encode(self, arg):
        """
        Encode an object corresponding to this argument as one or more words.
        Returns either a single string or a tuple of strings, the same as
        the encodeFunct passed to __init__.
        """

        words = self.encodeFunc(arg)
        if self.count == 1:
            assert type(words) == str
        else:
            # Alow encodeFunc to give a list instead of a tuple, because that's
            # close enough.
            assert type(words) in [tuple, list]
            assert len(words) == self.count
        return words

    def decode(self, words):
        """
        Parse one or more words into the appropriate type of object. The type
        of 'words' is the same as would be passed to the decodeFunc passed to
        __init__.
        """

        if self.count == 1:
            assert type(words) == str
        else:
            # Since words always comes from deserializeMessage, require that
            # it be a tuple, not a list. There's no real problem with it being
            # a list, but we know that that shouldn't happen, so if it does,
            # then it suggests a bug.
            assert type(words) == tuple
            assert len(words) == self.count
        return self.decodeFunc(words)

# For an arbitrary string command and an arbitrary list of strings args,
#     tokenize(buildMessage(command, args, lastIsUnsafe=<whatever>))
# should either return exactly (command, args) or raise an InvalidMessageError.
def tokenize(message):
    if not message:
        raise InvalidMessageError(message, "Empty message.")
    if message[0] == START_STRING:
        raise InvalidMessageError(message,
                                  "Message starts with unsafe string.")

    index = message.find(TOKEN_DELIM + START_STRING)
    if index == -1:
        tokens = message.split(TOKEN_DELIM)
    else:
        tokens = message[:index].split(TOKEN_DELIM) + [message[index + 2:]]

    if not all(tokens):
        log.warning("Empty token in {}.".format(tokens))

    return (tokens[0], tokens[1:])

# TODO: We can and should unit-test buildMessage.
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
        # TODO [#45]: Validate this.
        if command.startswith(START_STRING):
            raise InvalidMessageError(message, "{0} may not start with {0!r}"
                                               .format(tokenDesc,
                                                       START_STRING))

    checkToken(command, "Command")
    for arg in args:
        checkToken(arg, "Argument")

    # Checks passed; this is a valid message.
    return message


def badIMessageCommand(message, log):
    """
    Give an error for when a message originating from an internal source is
    received by a part of the code that doesn't know how to handle that type of
    message.
    """

    error = "Unrecognized command '{command}' in internal message." \
        .format(command=message.command)
    log.error(error)

    raise InvalidMessageError(message.serialize(), error)


def badEMessageCommand(message, log, clientId=None):
    """
    Log a warning for a message originating from an external source (ex: sent
    over the network), where the message is well-formed (valid command with the
    right number of arguments) but it was received by a part of the code that
    doesn't know how to handle that type of message.
    """

    sender = "external source"
    if clientId is not None:
        sender = "client {}".format(clientId)

    log.warning("Could not handle message type from {sender}: {command}"
                .format(sender=sender, command=message.command))


def badEMessageArgument(message, log, clientId=None, reason=""):
    """
    Log a warning for a message originating from an external source (ex: sent
    over the network), where the message is well-formed (valid command with the
    right number of arguments) and was received by a part of the code that
    knows how to handle that type of message, but one of the arguments to the
    message is invalid (for example, out of range).
    """

    sender = "external source"
    if clientId is not None:
        sender = "client {}".format(clientId)
    if reason:
        reason = "\n    " + reason

    log.warning("Invalid argument to message from {sender}: {message}{reason}"
                .format(sender=sender, message=message, reason=reason))


def illFormedEMessage(error, log, clientId=None):
    """
    Log a warning for when a message string originating from an external source
    could not be parsed into a message, for example because it used a
    nonexistent command or passed the wrong number of arguments.
    """

    sender = "external source"
    if clientId is not None:
        sender = "client {}".format(clientId)

    log.warning("Received invalid message from {sender}: {error}"
                .format(sender=sender, error=error))


# Note: if we get a completely invalid message from an internal source,
# deserializeMessage will already raise an exception, and we'll just let that
# exception propagate. So we don't need a fourth function for that case.


class InvalidMessageError(StandardError):
    def __init__(self, badMessage, errorDesc):
        self.badMessage = badMessage
        self.errorDesc  = errorDesc

    def __str__(self):
        return "{desc}  (Message is: {msg!r})".format(desc = self.errorDesc,
                                                      msg  = self.badMessage)

