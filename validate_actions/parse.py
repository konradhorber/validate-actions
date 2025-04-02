from yaml import *
from typing import Dict, List, Tuple, Union

ANY_VALUE = Union[ScalarToken, List, Dict]

def parse_flow_value(tokens: List[Token], index: int = 0) -> Tuple[ANY_VALUE, int]:
    token = tokens[index]
    
    if isinstance(token, ScalarToken):
        value = token
    elif isinstance(token, FlowMappingStartToken):
        value, index = parse_flow_mapping(tokens, index)
    elif isinstance(token, FlowSequenceStartToken):
        value, index = parse_flow_sequence(tokens, index)
    else:
        # TODO for now print out to console if anything else
        print("Unhandled token type:", token)
    
    return value, index

def parse_flow_sequence(tokens: List[Token], index: int = 0) -> Tuple[List[ANY_VALUE], int]:
    lst = []

    while index < len(tokens):
        token = tokens[index]
        if isinstance(token, FlowSequenceStartToken):
            pass

        elif isinstance(token, FlowEntryToken):
            pass
        elif isinstance(token, FlowSequenceEndToken):
            return lst, index
        
        else:
            # Process a value.
            value, index = parse_flow_value(tokens, index)
            lst.append(value)
        
        index += 1

     # TODO error handling
    print("Unhandled token type:", token)


def parse_flow_mapping(
        tokens: List[Token], 
        index: int = 0
    ) -> Tuple[
        Dict[ScalarToken, ANY_VALUE], 
        int
    ]:
    mapping = {}

    while index < len(tokens):
        token = tokens[index]

        if isinstance(token, FlowMappingStartToken):
            pass

        elif isinstance(token, FlowMappingEndToken):
            return mapping, index
        
        elif isinstance(token, KeyToken):
            index += 1
            key = tokens[index]
        
        elif isinstance(token, ValueToken):
            index += 1
            next_token = tokens[index]
            if isinstance(next_token, ScalarToken):
                mapping[key] = next_token
            elif isinstance(next_token, FlowMappingStartToken):
                mapping[key], index = parse_flow_mapping(tokens, index)
            elif isinstance(next_token, FlowSequenceStartToken):
                mapping[key], index = parse_flow_sequence(tokens, index)
            else:
                # TODO for now print out to console if anything else
                print("Unhandled token type:", next_token)
        
        else:
            # TODO for now print out to console if anything else
            print("Unhandled token type:", token)

        index += 1
    
     # TODO error handling
    print("Unhandled token type:", token)


def parse_block_value(tokens: Token, index: int = 0) -> Tuple[ANY_VALUE, int]:
    token = tokens[index]

    # value is a scalar
    if isinstance(token, ScalarToken):
        value = token

    # value is a nested block mapping
    elif isinstance(token, BlockMappingStartToken):
        value, index = parse_block_mapping(tokens, index)

    # value is a block sequence
    # - x
    # - y
    elif isinstance(token, BlockSequenceStartToken):
        value, index = parse_block_sequence(tokens, index)
    # also block sequence but with a non-critical missing indent before the -
    elif (isinstance(token, BlockEntryToken)):
        value, index = parse_block_sequence_unindented(tokens, index)

    # value is a inline flow sequence [ x, y, z ]
    elif isinstance(token, FlowSequenceStartToken):
        value, index = parse_flow_sequence(tokens, index)

    # value is a inline flow mapping { x: y, z: w }
    elif isinstance(token, FlowMappingStartToken):
        value, index = parse_flow_mapping(tokens, index)
    
    # illegal token at value position
    else:
        # TODO for now print out to console if anything else
        print("Unhandled token type:", token)
    
    return value, index
   

def parse_block_sequence(tokens: List[Token], index: int = 0) -> Tuple[List[ANY_VALUE], int]:
    lst = []

    while index < len(tokens):
        token = tokens[index]

        if isinstance(token, BlockSequenceStartToken):
            pass

        elif isinstance(token, BlockEntryToken):
            pass

        elif isinstance(token, BlockEndToken):
            return lst, index
        
        else:
            # Process a value.
            value, index = parse_block_value(tokens, index)
            lst.append(value)

        index += 1
    
    # TODO error handling
    print("Unhandled token type:", token)

def parse_block_sequence_unindented(
        tokens: List[Token], 
        index: int = 0
    ) -> Tuple[List[ANY_VALUE], int]:
    lst = []

    while index < len(tokens):
        token = tokens[index]

        if isinstance(token, BlockEntryToken):
            pass
        
        else:
            # Process a value.
            value, index = parse_block_value(tokens, index)
            lst.append(value)
            next = tokens[index + 1]
            if not isinstance(next, BlockEntryToken):
                return lst, index

        index += 1
    
    # TODO error handling
    print("Unhandled token type:", token)

    

def parse_block_mapping(
        tokens: List[Token], 
        index: int = 0
    ) -> Tuple[
        Dict[ScalarToken, ANY_VALUE],
        int]:
    mapping = {}
    while index < len(tokens):
        token = tokens[index]

        # Start of the block mapping
        if isinstance(token, BlockMappingStartToken):
            pass

        # When we hit the end of a block, return the mapping and the next index.
        elif isinstance(token, BlockEndToken):
            return mapping, index

        # Process a key.
        elif isinstance(token, KeyToken):
            # The token after KeyToken is the actual key
            index += 1
            next_token = tokens[index] 

            if isinstance(next_token, ScalarToken):
                key = next_token

            else:
                # TODO error handling
                print("Unhandled token type:", next_token)
        
        # Process a value.
        elif isinstance(token, ValueToken):
            # The token after ValueToken is the actual value
            index += 1
            value, index = parse_block_value(tokens, index)
            mapping[key] = value
        
        else:
            # TODO error handling
            print("Unhandled token type:", token)

        index += 1

def parse_workflow(content: str) -> Dict[ScalarToken, ANY_VALUE]:
    tokens = list(
        scan(content, Loader=SafeLoader)
    )

    content = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if isinstance(token, StreamStartToken):
            pass
        elif isinstance(token, StreamEndToken):
            return content
        elif isinstance(token, BlockMappingStartToken):
            content, i = parse_block_mapping(tokens, i)
        elif isinstance(token, BlockEntryToken):
            pass
        else:
            # TODO error handling
            print("Unhandled token type:", token)
        
        i += 1