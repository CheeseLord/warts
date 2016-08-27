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
                raise ValueError, "Message starts with unbounded string."
            tok  = message[len(START_STRING):]
            rest = ""
        else:
            tok, _, rest = message.partition(TOKEN_DELIM)
        tokens.append(tok)
        message = rest

    if not tokens:
        raise ValueError, "Empty message."

    return (tokens[0], tokens[1:])

