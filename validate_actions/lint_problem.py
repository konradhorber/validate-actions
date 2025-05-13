
# TODO fix this 
class LintProblem:
    """Represents a linting problem"""
    def __init__(self, 
                 pos, 
                 level: str, 
                 desc: str, 
                 rule: str):
        #: Line on which the problem was found (starting at 1)
        self.line: int = pos.line
        #: Column on which the problem was found (starting at 1)
        self.column: int = pos.col
        #: Warning or error
        self.level: str = level
        #: Human-readable description of the problem
        self.desc: str = desc
        #: Identifier of the rule that detected the problem
        self.rule: str = rule