"""Primitive building blocks for creating a GHA ast."""
from dataclasses import dataclass, field
from typing import List

from yaml import ScalarToken, Token


@dataclass
class Pos:
    """Position information for tracking locations in YAML source files.

    This class provides precise position tracking for AST nodes, enabling accurate
    error reporting and automatic fixes. Position information includes line number,
    column number, and character index within the file.

    Attributes:
        line: Zero-based line number in the source file
        col: Zero-based column number within the line
        idx: Character index from start of file

    Examples:
        Creating a position from YAML token:
            pos = Pos.from_token(token)

        Manual position creation:
            pos = Pos(line=5, col=10, idx=125)
    """

    line: int
    col: int
    idx: int = 0  # TODO: this is not ideal. should be done properly. Let's see with other fixes

    @classmethod
    def from_token(cls, token: Token) -> "Pos":
        """Creates a Pos instance from a PyYAML token.

        Args:
            token: PyYAML token containing position information

        Returns:
            Pos: Position object with line and column from the token
        """
        return cls(token.start_mark.line, token.start_mark.column)


@dataclass(frozen=True)
class Expression:
    """Represents a GitHub Actions expression like ${{ context.value }}.

    Expressions are parsed from strings and broken down into parts for validation.
    Each expression maintains position information for error reporting.

    Attributes:
        pos: Position in the source file where this expression starts
        string: Raw expression string as it appears in the YAML
        parts: List of String objects representing parsed parts of the expression

    Examples:
        Expression for ${{ github.event.pull_request.number }}:
            expr = Expression(
                pos=Pos(5, 10),
                string="github.event.pull_request.number",
                parts=[String("github"), String("event"), String("pull_request"), String("number")]
            )
    """

    pos: "Pos"
    string: str
    parts: List["String"]


@dataclass
class String:
    """Represents a string value with position metadata and embedded expressions.

    This is the core string representation used throughout the AST. It preserves
    the original string content along with precise position information and any
    GitHub Actions expressions (${{ ... }}) found within the string.

    Attributes:
        string: The string value extracted from the YAML token
        pos: Position of the string in the source file (line and column)
        expr: List of Expression objects found within this string

    Examples:
        Simple string:
            s = String("hello world", Pos(1, 0))

        String with expression:
            s = String("Hello ${{ github.actor }}", pos, [expr])

        From YAML token:
            s = String.from_token(scalar_token)
    """

    string: str
    pos: "Pos"
    expr: List[Expression] = field(default_factory=list)

    @classmethod
    def from_token(cls, token: ScalarToken) -> "String":
        """Creates a String instance from a PyYAML ScalarToken.

        Args:
            token: ScalarToken containing string value and position information

        Returns:
            String: String object with value and position from the token
        """
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
