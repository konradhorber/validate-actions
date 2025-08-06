from dataclasses import dataclass, field
from typing import List

from yaml import ScalarToken, Token


@dataclass
class Pos:
    line: int
    col: int
    idx: int = 0  # TODO: this is not ideal. should be done properly. Let's see with other fixes

    @classmethod
    def from_token(cls, token: Token) -> "Pos":
        """Creates a Pos instance from a YAML token."""
        return cls(token.start_mark.line, token.start_mark.column)


@dataclass(frozen=True)
class Expression:
    pos: "Pos"
    string: str
    parts: List["String"]


@dataclass
class String:
    """Represents a string value along with its positional metadata."""

    string: str
    """The string value extracted from the token."""
    pos: "Pos"
    """The position of the string in the source, including line and column."""

    expr: List[Expression] = field(default_factory=list)

    @classmethod
    def from_token(cls, token: ScalarToken) -> "String":
        """Creates a String instance from a PyYAML ScalarToken."""
        return cls(token.value, Pos.from_token(token))

    def __eq__(self, other):
        """Compare only based on string content."""
        if isinstance(other, String):
            return self.string == other.string
        elif isinstance(other, str):
            return self.string == other
        return NotImplemented

    def __hash__(self):
        """Hash only based on string content."""
        return hash(self.string)

    def __str__(self):
        """Ergonomic helper for string representation."""
        return self.string

    def __repr__(self):
        """String representation for debugging."""
        return f"String({self.string!r})"
