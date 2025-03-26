import yaml

def find_index_of(value: str, token_type: yaml.Token, tokens: list[yaml.Token]) -> int:
    for i, token in enumerate(tokens):
        if not isinstance(token, token_type):
            continue
        if not token.value == value:
            continue
        return i
    return -1