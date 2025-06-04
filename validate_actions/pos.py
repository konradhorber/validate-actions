from dataclasses import dataclass

from yaml import Token


@dataclass
class Pos:
    line: int
    col: int
    idx: int = 0  # TODO: this is not ideal. should be done properly. Let's see with other fixes

    @classmethod
    def from_token(cls, token: Token) -> 'Pos':
        """Creates a Pos instance from a YAML token."""
        return cls(token.start_mark.line, token.start_mark.column)
