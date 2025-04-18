import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from validate_actions.lint_problem import LintProblem
from validate_actions.workflow.ast import Pos, String


class YAMLParser(ABC):
    """Abstract base class for YAML parser implementations.

    Args:
        ABC: Abstract base class from the abc module.
    """
    @abstractmethod
    def parse(self, file: Path) -> Tuple[Dict[String, Any], List[LintProblem]]:
        """Parse a YAML file into a structured representation.

        Args:
            file (Path): Path to the YAML file to parse.

        Returns:
            Tuple[Dict[String, Any], List[LintProblem]]: A tuple containing
                the parsed YAML content as a dictionary and a list of lint
                problems found during parsing.
        """
        pass


class PyYAMLParser(YAMLParser):
    """YAML parser implementation using PyYAML.

    Args:
        YAMLParser: Abstract base class for YAML parsers.
    """

    def __init__(self) -> None:
        """Initialize the PyYAMLParser.
        """
        self.problems: List[LintProblem] = []
        self.RULE = 'actions_syntax-error'

    def parse(self, file: Path) -> Tuple[Dict[String, Any], List[LintProblem]]:
        """Parse a YAML file into a structured representation using PyYAML.

        Args:
            file (Path): Path to the YAML file to parse.

        Returns:
            Tuple[Dict[String, Any], List[LintProblem]]: A tuple containing
                the parsed YAML content as a dictionary and a list of lint
                problems found during parsing.
        """

        # Read file from I/O
        try:
            with open(file, 'r') as f:
                buffer = f.read()
        except OSError as e:
            print(e, file=sys.stderr)
            self.problems.append(LintProblem(
                pos=Pos(0, 0),
                desc=f"Error reading from file system for {file}",
                level='error',
                rule=self.RULE
            ))
            return {}, self.problems

        # Use PyYAML to parse the file as a flat list of tokens
        try:
            tokens = list(yaml.scan(buffer, Loader=yaml.SafeLoader))
        except yaml.error.MarkedYAMLError as e:
            self.problems.append(LintProblem(
                pos=Pos(0, 0),
                desc=f"Error parsing YAML file: {e}",
                level='error',
                rule=self.RULE
            ))
            return {}, self.problems

        # Process the tokens to build a structured representation
        content: Dict[String, Any] = {}
        error_desc = 'Error parsing top-level workflow structure'
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if isinstance(token, yaml.StreamStartToken):
                pass
            elif isinstance(token, yaml.StreamEndToken):
                return content, self.problems
            elif isinstance(token, yaml.BlockMappingStartToken):
                content, i = self.__parse_block_mapping(tokens, i)
            elif isinstance(token, yaml.BlockEntryToken):
                pass
            else:
                self.problems.append(LintProblem(
                    pos=Pos(0, 0),
                    desc=error_desc,
                    level='error',
                    rule=self.RULE
                ))

            i += 1

        # If we reach here, it means there's an unexpected error in the
        # workflow structure
        self.problems.append(LintProblem(
            pos=Pos(0, 0),
            desc=error_desc,
            level='error',
            rule=self.RULE
        ))
        return {}, self.problems

    def __parse_block_mapping(
        self,
        tokens: List[yaml.Token],
        index: int = 0
    ) -> Tuple[
        Dict[String, Any],
        int
    ]:
        """Parse a YAML block mapping into a dictionary.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[Dict[String, Any], int]: The parsed dictionary and the new
                index position.
        """
        mapping: Dict[String, Any] = {}
        error_desc = 'Error parsing block mapping'
        while index < len(tokens):
            token = tokens[index]

            # Start of the block mapping
            if isinstance(token, yaml.BlockMappingStartToken):
                pass

            # When we hit the end of a block, return mapping and next index
            elif isinstance(token, yaml.BlockEndToken):
                return mapping, index

            # Process a key.
            elif isinstance(token, yaml.KeyToken):
                # The token after KeyToken is the actual key
                index += 1
                next_token = tokens[index]

                if isinstance(next_token, yaml.ScalarToken):
                    key = String.from_token(next_token)

                else:
                    self.problems.append(LintProblem(
                        pos=Pos.from_token(next_token),
                        desc=error_desc,
                        level='error',
                        rule=self.RULE
                    ))

            # Process a value.
            elif isinstance(token, yaml.ValueToken):
                # The token after ValueToken is the actual value
                index += 1
                value, index = self.__parse_block_value(tokens, index)
                mapping[key] = value

            else:
                self.problems.append(LintProblem(
                    pos=Pos.from_token(token),
                    desc=error_desc,
                    level='error',
                    rule=self.RULE
                ))

            index += 1

        # If we reach here, it means there's an unexpected error in the
        # block mapping
        self.problems.append(LintProblem(
            pos=Pos.from_token(tokens[index]),
            desc=error_desc,
            level='error',
            rule=self.RULE
        ))
        return {}, index

    def __parse_block_value(
        self, tokens: List[yaml.Token], index: int = 0
    ) -> Tuple[Any, int]:
        """Parse a YAML block value into the appropriate Python type.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[Any, int]: The parsed value and the new index position.
        """
        token = tokens[index]

        value: Any

        # value is a scalar
        if isinstance(token, yaml.ScalarToken):
            value = self.__parse_scalar_value(token)

        # value is a nested block mapping
        elif isinstance(token, yaml.BlockMappingStartToken):
            value, index = self.__parse_block_mapping(tokens, index)

        # value is a block sequence
        # - x
        # - y
        elif isinstance(token, yaml.BlockSequenceStartToken):
            value, index = self.__parse_block_sequence(tokens, index)
        # also block sequence but with a non-critical missing indent before the
        # -
        elif (isinstance(token, yaml.BlockEntryToken)):
            value, index = self.__parse_block_sequence_unindented(
                tokens, index
            )

        # value is a inline flow sequence [ x, y, z ]
        elif isinstance(token, yaml.FlowSequenceStartToken):
            value, index = self.__parse_flow_sequence(tokens, index)

        # value is a inline flow mapping { x: y, z: w }
        elif isinstance(token, yaml.FlowMappingStartToken):
            value, index = self.__parse_flow_mapping(tokens, index)

        # illegal token at value position
        else:
            self.problems.append(LintProblem(
                pos=Pos.from_token(tokens[index]),
                desc='Error parsing block value',
                level='error',
                rule=self.RULE
            ))

        return value, index

    def __parse_block_sequence(
        self,
        tokens: List[yaml.Token],
        index: int = 0
    ) -> Tuple[List[Any], int]:
        """Parse a YAML block sequence into a list.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[List[Any], int]: The parsed list and the new index position.
        """
        lst: Any = []

        while index < len(tokens):
            token = tokens[index]

            if isinstance(token, yaml.BlockSequenceStartToken):
                pass

            elif isinstance(token, yaml.BlockEntryToken):
                pass

            elif isinstance(token, yaml.BlockEndToken):
                return lst, index

            else:
                # Process a value.
                value, index = self.__parse_block_value(tokens, index)
                lst.append(value)

            index += 1

        # If we reach here, it means there's an unexpected error in the
        # block sequence
        self.problems.append(LintProblem(
            pos=Pos.from_token(tokens[index]),
            desc='Error parsing block sequence',
            level='error',
            rule=self.RULE
        ))
        return [], index

    def __parse_block_sequence_unindented(
        self,
        tokens: List[yaml.Token],
        index: int = 0
    ) -> Tuple[List[Any], int]:
        """Parse an unindented YAML block sequence into a list.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[List[Any], int]: The parsed list and the new index position.
        """
        lst = []

        while index < len(tokens):
            token = tokens[index]

            if isinstance(token, yaml.BlockEntryToken):
                pass

            else:
                # Process a value.
                value, index = self.__parse_block_value(tokens, index)
                lst.append(value)
                next = tokens[index + 1]
                if not isinstance(next, yaml.BlockEntryToken):
                    return lst, index

            index += 1

        # If we reach here, it means there's an unexpected error in the
        # block sequence
        self.problems.append(LintProblem(
                pos=Pos.from_token(tokens[index]),
                desc='Error parsing block sequence',
                level='error',
                rule=self.RULE
            ))
        return [], index

    def __parse_flow_mapping(
        self,
        tokens: List[yaml.Token],
        index: int = 0
    ) -> Tuple[
        Dict[String, Any],
        int
    ]:
        """Parse a YAML flow mapping into a dictionary.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[Dict[String, Any], int]: The parsed dictionary and the new
                index position.
        """
        mapping: Dict[String, Any] = {}
        error_desc = 'Error parsing flow mapping'

        while index < len(tokens):
            token = tokens[index]

            if isinstance(token, yaml.FlowMappingStartToken):
                pass

            elif isinstance(token, yaml.FlowMappingEndToken):
                return mapping, index

            elif isinstance(token, yaml.KeyToken):
                index += 1
                next_token = tokens[index]

                if isinstance(next_token, yaml.ScalarToken):
                    key = String.from_token(next_token)

                else:
                    self.problems.append(LintProblem(
                        pos=Pos.from_token(next_token),
                        desc=error_desc,
                        level='error',
                        rule=self.RULE
                    ))

            elif isinstance(token, yaml.ValueToken):
                index += 1
                next_token = tokens[index]
                if isinstance(next_token, yaml.ScalarToken):
                    value = self.__parse_scalar_value(next_token)
                    mapping[key] = value
                elif isinstance(next_token, yaml.FlowMappingStartToken):
                    mapping[key], index = self.__parse_flow_mapping(
                        tokens,
                        index
                    )
                elif isinstance(next_token, yaml.FlowSequenceStartToken):
                    mapping[key], index = self.__parse_flow_sequence(
                        tokens,
                        index
                    )
                else:
                    self.problems.append(LintProblem(
                        pos=Pos.from_token(next_token),
                        desc=error_desc,
                        level='error',
                        rule=self.RULE
                    ))

            else:
                self.problems.append(LintProblem(
                    pos=Pos.from_token(token),
                    desc=error_desc,
                    level='error',
                    rule=self.RULE
                ))

            index += 1

        # If we reach here, it means there's an unexpected error in the
        # flow mapping
        self.problems.append(LintProblem(
            pos=Pos.from_token(tokens[index]),
            desc=error_desc,
            level='error',
            rule=self.RULE
        ))
        return {}, index

    def __parse_flow_sequence(
        self,
        tokens: List[yaml.Token],
        index: int = 0
    ) -> Tuple[List[Any], int]:
        """Parse a YAML flow sequence into a list.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[List[Any], int]: The parsed list and the new index position.
        """
        lst: List[Any] = []

        while index < len(tokens):
            token = tokens[index]
            if isinstance(token, yaml.FlowSequenceStartToken):
                pass

            elif isinstance(token, yaml.FlowEntryToken):
                pass
            elif isinstance(token, yaml.FlowSequenceEndToken):
                return lst, index

            else:
                # Process a value.
                value, index = self.__parse_flow_value(tokens, index)
                lst.append(value)

            index += 1

        self.problems.append(LintProblem(
            pos=Pos.from_token(tokens[index]),
            desc='Error parsing flow sequence',
            level='error',
            rule=self.RULE
        ))
        return [], index

    def __parse_flow_value(
        self,
        tokens: List[yaml.Token],
        index: int = 0
    ) -> Tuple[Any, int]:
        """Parse a YAML flow value into the appropriate Python type.

        Args:
            tokens (List[yaml.Token]): The list of YAML tokens.
            index (int, optional): The current index in the token list.
                Defaults to 0.

        Returns:
            Tuple[Any, int]: The parsed value and the new index position.
        """
        token = tokens[index]
        value: Any
        if isinstance(token, yaml.ScalarToken):
            value = self.__parse_scalar_value(token)
        elif isinstance(token, yaml.FlowMappingStartToken):
            value, index = self.__parse_flow_mapping(tokens, index)
        elif isinstance(token, yaml.FlowSequenceStartToken):
            value, index = self.__parse_flow_sequence(tokens, index)
        else:
            self.problems.append(LintProblem(
                pos=Pos.from_token(token),
                desc='Error parsing flow value',
                level='error',
                rule=self.RULE
            ))

        return value, index

    def __parse_scalar_value(
        self,
        token: yaml.ScalarToken
    ):
        """Parse a scalar token into the appropriate Python type (bool, int, float, or String).

        Args:
            token (yaml.ScalarToken): The scalar token to parse.

        Returns:
            Any: The parsed value as the appropriate Python type.
        """
        val = token.value

        # Boolean handling
        if isinstance(val, bool):
            return val
        elif val == 'true':
            return True
        elif val == 'false':
            return False

        # Number handling
        try:
            # First try to parse as int if possible
            if str(int(float(val))) == val:
                return int(val)
            # Otherwise parse as float
            return float(val)
        except (ValueError, TypeError):
            # If not a boolean or number, return as String
            return String.from_token(token)
