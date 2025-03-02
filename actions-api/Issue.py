
class Issue:
    def __init__(self, line, column, level, desc='<no description>', rule=None):
        #: Line on which the problem was found (starting at 1)
        self.line = line
        #: Column on which the problem was found (starting at 1)
        self.column = column
        #: Level of problem (error, warning, info)
        self.level = level
        #: Human-readable description of the problem
        self.desc = desc
        #: Identifier of the rule that detected the problem
        self.rule = rule


    def __str__(self) -> str:
        return f'  [not bold bright_black]{self.line}:{self.column}[/not bold bright_black]       [red]{self.level}[/red]    {self.desc}  [bright_black]({self.rule})[/bright_black]'