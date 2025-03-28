import yaml
from typing import Iterable

def find_index_of(value: str, token_type: yaml.Token, tokens: list[yaml.Token]) -> Iterable[int]:
    for i, token in enumerate(tokens):
        if isinstance(token, token_type) and token.value == value:
            yield i