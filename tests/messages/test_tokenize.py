import pytest

from src.shared.message_infrastructure import START_STRING, TOKEN_DELIM
from src.shared.message_infrastructure import tokenize, buildMessage
from src.shared.message_infrastructure import InvalidMessageError


class TestTokenize:
    """
    Make sure we can tokenize a message correctly.
    """

    def test_basic(self):
        assert TOKEN_DELIM == ' '

        with pytest.raises(InvalidMessageError):
            tokenize("")

        assert tokenize("a")     == ("a", [])
        assert tokenize(" a")    == ("", ["a"])
        assert tokenize("a ")    == ("a", [""])
        assert tokenize("  a  ") == ("", ["", "a", "", ""])

        assert tokenize("a b")  == ("a", ["b"])
        assert tokenize("a  b") == ("a", ["", "b"])
        assert tokenize(" a b") == ("", ["a", "b"])
        assert tokenize("a b ") == ("a", ["b", ""])

        assert tokenize("ab")    == ("ab", [])
        assert tokenize("ab cd") == ("ab", ["cd"])

    def test_unsafe(self):
        assert TOKEN_DELIM == ' '
        assert START_STRING == '|'

        assert tokenize("a |b")    == ("a", ["b"])
        assert tokenize("a |")     == ("a", [""])
        assert tokenize("a b|")    == ("a", ["b|"])
        assert tokenize("a b|c")   == ("a", ["b|c"])
        assert tokenize("a |b c")  == ("a", ["b c"])
        assert tokenize("a |b |c") == ("a", ["b |c"])

        with pytest.raises(InvalidMessageError):
            tokenize("|a b")

    def test_invertible(self):
        assert TOKEN_DELIM == ' '
        assert START_STRING == '|'
        
        message = "ab cd ef"
        tokens  = ("ab", ["cd", "ef"])
        assert tokenize(message) == tokens
        assert buildMessage(*tokens, lastIsUnsafe=False) == message

        message = "ab |cd ef"
        tokens  = ("ab", ["cd ef"])
        assert tokenize(message) == tokens
        assert buildMessage(*tokens, lastIsUnsafe=True) == message

