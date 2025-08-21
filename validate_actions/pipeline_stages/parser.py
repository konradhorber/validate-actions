"""Parser for YAML files, from input file to Python data structure representation."""
import copy
import re
import sys
from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import yaml

from validate_actions.domain_model.primitives import Expression, Pos, String
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.globals.process_stage import ProcessStage


class YAMLParser(ProcessStage[Path, Dict[String, Any]]):
    """Abstract base class for parsing GitHub Actions workflow YAML files.
    
    This parser performs token-level parsing to enable precise position tracking
    and auto-fixing of workflow files. The parser maintains exact line, column,
    and character positions for all parsed elements to support:
    
    - Validation rule error reporting with precise locations
    - Auto-fixing of problems using character-level edits
    - Expression parsing within ${{ }} syntax
    - Structured AST construction for downstream pipeline stages
    """

    @abstractmethod
    def process(self, file: Path) -> Dict[String, Any]:
        """Parse a GitHub Actions workflow YAML file into a structured representation.

        Converts YAML content into a dictionary with String keys that preserve
        position information for validation and auto-fixing. Handles GitHub
        Actions-specific constructs including expressions and complex nested
        structures.

        Args:
            file (Path): Path to the GitHub Actions workflow YAML file to parse.

        Returns:
            Dict[String, Any]: Parsed YAML as dictionary with position-aware String
                keys and values. Returns empty dict if parsing fails or file is invalid.
        """
        pass


class PyYAMLParser(YAMLParser):
    """YAML parser implementation using PyYAML."""

    def __init__(self, problems: Problems) -> None:
        """Initialize the PyYAMLParser."""
        super().__init__(problems)
        self.RULE = "yaml-syntax"

    def process(self, file: Path) -> Dict[String, Any]:
        """Parse a YAML file into a structured representation using PyYAML.

        Args:
            file (Path): Path to the YAML file to parse.

        Returns:
            Dict[String, Any]: The parsed YAML content as a dictionary.
        """

        # Read file from I/O
        try:
            with open(file, "r") as f:
                buffer = f.read()
        except OSError as e:
            print(e, file=sys.stderr)
            self.problems.append(
                Problem(
                    pos=Pos(0, 0),
                    desc=f"Error reading from file system for {file}",
                    level=ProblemLevel.ERR,
                    rule=self.RULE,
                )
            )
            return {}

        # Use PyYAML to parse the file as a flat list of tokens
        try:
            tokens = list(yaml.scan(buffer, Loader=yaml.SafeLoader))
        except yaml.error.MarkedYAMLError as e:
            self.problems.append(
                Problem(
                    pos=Pos(0, 0),
                    desc=f"Error parsing YAML file: {e}",
                    level=ProblemLevel.ERR,
                    rule=self.RULE,
                )
            )
            return {}

        # Basic structure validation
        if not self._validate_basic_yaml_structure(tokens):
            self.problems.append(
                Problem(
                    pos=Pos(0, 0),
                    desc="File does not appear to be a valid GitHub Actions workflow YAML",
                    level=ProblemLevel.ERR,
                    rule=self.RULE,
                )
            )
            return {}

        # Process the tokens to build a structured representation
        content: Dict[String, Any] = {}
        error_desc = "Error parsing top-level workflow structure"
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if isinstance(token, yaml.StreamStartToken):
                pass
            elif isinstance(token, yaml.StreamEndToken):
                return content
            elif isinstance(token, yaml.BlockMappingStartToken):
                content, i = self.__parse_block_mapping(tokens, i)
            elif isinstance(token, yaml.BlockEntryToken):
                pass
            else:
                self.problems.append(
                    Problem(pos=Pos(0, 0), desc=error_desc, level=ProblemLevel.ERR, rule=self.RULE)
                )

            i += 1

        # If we reach here, it means there's an unexpected error in the
        # workflow structure
        self.problems.append(
            Problem(pos=Pos(0, 0), desc=error_desc, level=ProblemLevel.ERR, rule=self.RULE)
        )
        return {}

    def __parse_block_mapping(
        self, tokens: List[yaml.Token], index: int = 0
    ) -> Tuple[Dict[String, Any], int]:
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
        error_desc = "Error parsing block mapping"
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
                next_token = self.__safe_token_access(tokens, index)
                if next_token is None:
                    self.problems.append(
                        Problem(
                            pos=self.__parse_pos(token),
                            desc="Unexpected end of tokens while parsing key",
                            level=ProblemLevel.ERR,
                            rule=self.RULE,
                        )
                    )
                    return {}, index

                if isinstance(next_token, yaml.ScalarToken):
                    key = self.__parse_str(next_token)

                else:
                    self.problems.append(
                        Problem(
                            pos=self.__parse_pos(next_token),
                            desc=error_desc,
                            level=ProblemLevel.ERR,
                            rule=self.RULE,
                        )
                    )

            # Process a value.
            elif isinstance(token, yaml.ValueToken):
                # The token after ValueToken is the actual value
                index += 1
                if index >= len(tokens):
                    self.problems.append(
                        Problem(
                            pos=self.__parse_pos(token),
                            desc="Unexpected end of tokens while parsing value",
                            level=ProblemLevel.ERR,
                            rule=self.RULE,
                        )
                    )
                    return {}, index
                value, index = self.__parse_block_value(tokens, index)
                mapping[key] = value

            else:
                self.problems.append(
                    Problem(
                        pos=self.__parse_pos(token),
                        desc=error_desc,
                        level=ProblemLevel.ERR,
                        rule=self.RULE,
                    )
                )

            index += 1

        # If we reach here, it means there's an unexpected error in the
        # block mapping
        error_token = self.__safe_token_access(tokens, index)
        error_pos = self.__parse_pos(error_token) if error_token else Pos(0, 0, 0)
        self.problems.append(
            Problem(
                pos=error_pos,
                desc=error_desc,
                level=ProblemLevel.ERR,
                rule=self.RULE,
            )
        )
        return {}, index

    def __parse_block_value(self, tokens: List[yaml.Token], index: int = 0) -> Tuple[Any, int]:
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
        elif isinstance(token, yaml.BlockEntryToken):
            value, index = self.__parse_block_sequence_unindented(tokens, index)

        # value is a inline flow sequence [ x, y, z ]
        elif isinstance(token, yaml.FlowSequenceStartToken):
            value, index = self.__parse_flow_sequence(tokens, index)

        # value is a inline flow mapping { x: y, z: w }
        elif isinstance(token, yaml.FlowMappingStartToken):
            value, index = self.__parse_flow_mapping(tokens, index)

        # else assume empty block mapping
        else:
            value = {}
            index -= 1  # Decrement index to reprocess current token

        return value, index

    def __parse_block_sequence(
        self, tokens: List[yaml.Token], index: int = 0
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
        error_token = self.__safe_token_access(tokens, index)
        error_pos = self.__parse_pos(error_token) if error_token else Pos(0, 0, 0)
        self.problems.append(
            Problem(
                pos=error_pos,
                desc="Error parsing block sequence",
                level=ProblemLevel.ERR,
                rule=self.RULE,
            )
        )
        return [], index

    def __parse_block_sequence_unindented(
        self, tokens: List[yaml.Token], index: int = 0
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
        self.problems.append(
            Problem(
                pos=self.__parse_pos(tokens[index]),
                desc="Error parsing block sequence",
                level=ProblemLevel.ERR,
                rule=self.RULE,
            )
        )
        return [], index

    def __parse_flow_mapping(
        self, tokens: List[yaml.Token], index: int = 0
    ) -> Tuple[Dict[String, Any], int]:
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
        error_desc = "Error parsing flow mapping"

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
                    key = self.__parse_str(next_token)

                else:
                    self.problems.append(
                        Problem(
                            pos=self.__parse_pos(next_token),
                            desc=error_desc,
                            level=ProblemLevel.ERR,
                            rule=self.RULE,
                        )
                    )

            elif isinstance(token, yaml.ValueToken):
                index += 1
                next_token = tokens[index]
                if isinstance(next_token, yaml.ScalarToken):
                    value = self.__parse_scalar_value(next_token)
                    mapping[key] = value
                elif isinstance(next_token, yaml.FlowMappingStartToken):
                    mapping[key], index = self.__parse_flow_mapping(tokens, index)
                elif isinstance(next_token, yaml.FlowSequenceStartToken):
                    mapping[key], index = self.__parse_flow_sequence(tokens, index)
                else:
                    self.problems.append(
                        Problem(
                            pos=self.__parse_pos(next_token),
                            desc=error_desc,
                            level=ProblemLevel.ERR,
                            rule=self.RULE,
                        )
                    )

            else:
                self.problems.append(
                    Problem(
                        pos=self.__parse_pos(token),
                        desc=error_desc,
                        level=ProblemLevel.ERR,
                        rule=self.RULE,
                    )
                )

            index += 1

        # If we reach here, it means there's an unexpected error in the
        # flow mapping
        error_token = self.__safe_token_access(tokens, index)
        error_pos = self.__parse_pos(error_token) if error_token else Pos(0, 0, 0)
        self.problems.append(
            Problem(
                pos=error_pos,
                desc=error_desc,
                level=ProblemLevel.ERR,
                rule=self.RULE,
            )
        )
        return {}, index

    def __parse_flow_sequence(
        self, tokens: List[yaml.Token], index: int = 0
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

        error_token = self.__safe_token_access(tokens, index)
        error_pos = self.__parse_pos(error_token) if error_token else Pos(0, 0, 0)
        self.problems.append(
            Problem(
                pos=error_pos,
                desc="Error parsing flow sequence",
                level=ProblemLevel.ERR,
                rule=self.RULE,
            )
        )
        return [], index

    def __parse_flow_value(self, tokens: List[yaml.Token], index: int = 0) -> Tuple[Any, int]:
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
            self.problems.append(
                Problem(
                    pos=self.__parse_pos(token),
                    desc="Error parsing flow value",
                    level=ProblemLevel.ERR,
                    rule=self.RULE,
                )
            )

        return value, index

    def __parse_scalar_value(self, token: yaml.ScalarToken):
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
        elif val == "true":
            return True
        elif val == "false":
            return False

        # Number handling
        try:
            # First try to parse as int if possible
            if str(int(float(val))) == val:
                return int(val)
            # Otherwise parse as float
            return float(val)
        except ValueError:
            # If not a boolean or number, return as String
            return self.__parse_str(token)

    def __parse_str(self, token: yaml.ScalarToken) -> String:
        """
        Reads a string and returns a String object.
        """
        token_string: str = token.value
        token_pos = self.__parse_pos(token)

        # parse expressions in the form of ${{ ... }}
        # we need the full string to calc indices for expression fixing
        pattern = r"\${{\s*(.*?)\s*}}"
        full_str: str = token.start_mark.buffer
        token_full_str = full_str[token.start_mark.index : token.end_mark.index]
        matches = re.finditer(pattern, token_full_str)  # finds expressions in token string
        expressions = self._parse_expressions(matches, token_pos, token)

        return String(token_string, token_pos, expressions)

    def __parse_pos(self, token: yaml.Token) -> Pos:
        """
        Reads a token and returns a Pos object.
        """
        return Pos(token.start_mark.line, token.start_mark.column, token.start_mark.index)

    def __safe_token_access(self, tokens: List[yaml.Token], index: int) -> Optional[yaml.Token]:
        """
        Safely access a token at the given index, returning None if out of bounds.
        """
        if 0 <= index < len(tokens):
            return tokens[index]
        return None

    def _parse_expressions(
        self, matches: Iterator[re.Match[str]], token_pos: Pos, token: yaml.ScalarToken
    ) -> List[Expression]:
        """
        Parses expressions from the matches and builds an expression list.
        """
        expressions: List[Expression] = []
        # for each expression in the list of matches (expressions)
        for match_obj in matches:
            # extract the expression string
            expr_str = match_obj.group(1)

            # Split expression into parts on dots
            raw_parts_list = expr_str.split(".")
            parts_ast_nodes = []

            # determine the character index of the part
            # first part begins at the start of the expression
            part_pos = copy.copy(token_pos)
            part_start_char_idx = match_obj.start(1)
            part_pos.idx = token.start_mark.index + part_start_char_idx

            # for each part in the expression
            for i, part_segment_str in enumerate(raw_parts_list):
                # check for bracket access like object['property'] in the part
                bracket_match_obj = re.match(r"(\w+)\[['\"](.+)['\"]\]", part_segment_str)

                if bracket_match_obj:
                    main_name_str = bracket_match_obj.group(1)  # first part e.g., 'ports'
                    parts_ast_nodes.append(String(main_name_str, part_pos))

                    content_in_brackets_str = bracket_match_obj.group(2)  # second part e.g. '6379'
                    # calculate offset of second part within part_segment_str
                    # the start of group(2) is relative to the start of part_segment_str
                    part_pos.idx += bracket_match_obj.start(2)
                    parts_ast_nodes.append(String(content_in_brackets_str, part_pos))
                else:
                    # Simple part (no brackets)
                    parts_ast_nodes.append(String(part_segment_str, part_pos))

                part_pos = copy.copy(part_pos)
                # Advance the offset within expr_str for the next part
                part_pos.idx += len(part_segment_str)
                if i < len(raw_parts_list) - 1:  # If not the last part, account for the dot
                    part_pos.idx += 1

            expressions.append(
                Expression(
                    pos=token_pos,  # Pos of the start of the part
                    string=expr_str,  # The full expression string
                    parts=parts_ast_nodes,  # List of String objects for each part
                )
            )

        return expressions

    def _validate_basic_yaml_structure(self, tokens: List[yaml.Token]) -> bool:
        """Basic validation that this looks like a GitHub Actions workflow.

        Checks for minimal expected structure:
        - Contains at least a mapping structure
        - Not just empty or whitespace
        - Has reasonable token count
        """
        if not tokens:
            return False

        # Must have at least stream start/end and some content
        if len(tokens) < 3:
            return False

        # Should start with StreamStart and contain at least one mapping
        has_stream_start = any(isinstance(token, yaml.StreamStartToken) for token in tokens)
        has_mapping = any(isinstance(token, yaml.BlockMappingStartToken) for token in tokens)
        has_stream_end = any(isinstance(token, yaml.StreamEndToken) for token in tokens)

        return has_stream_start and has_mapping and has_stream_end
