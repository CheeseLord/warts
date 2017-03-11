import pytest

from src.shared.message_infrastructure import START_STRING, TOKEN_DELIM
from src.shared.message_infrastructure import tokenize, InvalidMessageError


class TestTokenize:
    """
    Make sure we can tokenize a message correctly.
    """

    def test_basic(self):
        assert TOKEN_DELIM == ' '

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
        assert tokenize("a b|")    == ("a", ["b|"])
        assert tokenize("a b|c")   == ("a", ["b|c"])
        assert tokenize("a |b c")  == ("a", ["b c"])
        assert tokenize("a |b |c") == ("a", ["b |c"])

        with pytest.raises(InvalidMessageError):
            tokenize("|a b")

