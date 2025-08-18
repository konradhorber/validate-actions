# validate-actions Development Guide 🛠️

This document provides comprehensive development setup, architecture overview, and contribution guidelines for the validate-actions project.

---

## 🚀 Quick Development Setup

### Prerequisites
- Python 3.12+
- Poetry (others possible but docs focus on it)
- Git

### Getting Started
```bash
# Clone the repository
git clone https://github.com/konradhorber/validate-actions
cd validate-actions

# Install dependencies (including dev dependencies)
poetry install --with dev

# Run validate-actions in development mode
poetry run validate-actions

# Run with specific workflow file
poetry run validate-actions .github/workflows/ci.yml

# Run with auto-fix enabled
poetry run validate-actions --fix

# Run with warning limits
poetry run validate-actions --max-warnings 5
```

---

## 🏗️ Architecture Overview

### Core Design Principles

**validate-actions** is built around a **pipeline architecture** with **token-level YAML parsing** for maximum precision and auto-fixing capabilities.

#### Key Architectural Decisions:
1. **PyYAML Token-Level Parsing**: Uses PyYAML at the token level (not high-level APIs) for precise position tracking
2. **Custom AST**: Domain-specific Abstract Syntax Tree preserving GitHub Actions semantics
3. **Pipeline Processing**: Modular stages for parsing → building → enriching → validating
4. **Rule-Based Validation**: Pluggable validation rules with fixing capabilities
5. **Position Preservation**: Every AST node maintains exact source positions for error reporting

### Architecture Diagram
tbd

---

## 📁 Project Structure

```
validate_actions/
├── __init__.py              # Main API surface (validate_workflow function)
├── main.py                  # CLI entry point (Typer app)
├── cli.py                   # CLI orchestration and user interface
├── pipeline.py              # Main validation pipeline coordinator
│
├── cli_components/          # CLI building blocks
│   ├── output_formatter.py    # Colored terminal output
│   └── result_aggregator.py   # Result collection and summarization
│
├── domain_model/           # Core domain types and AST
│   ├── ast.py                 # GitHub Actions workflow AST nodes
│   ├── contexts.py            # GitHub Actions context definitions
│   ├── primitives.py          # Basic types (Pos, String, Expression)
│   └── job_order_models.py    # Job dependency graph models
│
├── globals/                # Shared utilities and configurations
│   ├── cli_config.py          # CLI configuration management
│   ├── fixer.py              # Automatic text editing and fixes
│   ├── problems.py           # Problem reporting and collection
│   ├── process_stage.py      # Base class for pipeline stages
│   ├── validation_result.py  # Validation result aggregation
│   └── web_fetcher.py        # GitHub API integration
│
├── pipeline_stages/        # Modular validation pipeline
│   ├── parser.py             # PyYAML token-level parsing
│   ├── builder.py            # AST construction from parsed data
│   ├── marketplace_enricher.py  # GitHub Actions marketplace integration
│   ├── job_orderer.py        # Job dependency analysis
│   ├── validator.py          # Rule execution coordinator
│   └── builders/             # Specialized AST builders
│       ├── workflow_builder.py
│       ├── jobs_builder.py
│       ├── steps_builder.py
│       └── events_builder.py
│
└── rules/                  # Validation rule implementations
    ├── rule.py               # Base Rule class and interfaces
    ├── expressions_contexts.py  # GitHub context validation
    ├── action_metadata.py    # Action usage and version validation
    ├── steps_io_match.py     # Step input/output validation
    └── rules.yml             # Rule configuration metadata
```

---

## 🔧 Development Commands

### Core Development Workflow
```bash
# Run the tool on sample workflows
poetry run validate-actions tests/resources/valid_workflow.yml

# Test auto-fixing capabilities
poetry run validate-actions tests/resources/fixable_workflow.yml --fix
```

### Testing Commands
```bash
# Run full test suite
poetry run pytest

# Run tests with coverage reporting
poetry run coverage run -m pytest
poetry run coverage report
poetry run coverage html  # Generate HTML coverage report

# Run specific test categories
poetry run pytest tests/rules_test/           # Rule-specific tests
poetry run pytest tests/workflow_test/        # AST and parsing tests
poetry run pytest tests/pipeline_stages_test/ # Pipeline component tests
```

### Code Quality Commands
```bash
# Format code
poetry run black validate_actions/
poetry run isort validate_actions/

# Lint code
poetry run flake8 validate_actions/

# Type checking
poetry run mypy validate_actions/

# Run all quality checks
poetry run black validate_actions/ && poetry run isort validate_actions/ && poetry run flake8 validate_actions/ && poetry run mypy validate_actions/
```

---

## 🧠 Core Concepts

### 1. Token-Level Parsing

**Why Token-Level?**
- **Precise Position Tracking**: Every AST node knows its exact location (line, column, character index)
- **Auto-fixing Capability**: Enable character-exact edits for automatic corrections
- **Expression Parsing**: Detect and parse `${{ ... }}` expressions within YAML strings

**Token Processing Pattern:**
```python
def parse_tokens(self, tokens: List[Token]) -> AST:
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if isinstance(token, yaml.BlockMappingStartToken):
            content, i = self.__parse_block_mapping(tokens, i)
        elif isinstance(token, yaml.ScalarToken):
            string_node = String.from_token(token)
            i += 1
        # ... handle other token types
    return ast_node
```

### 2. Position Tracking

Every AST node contains position information:
```python
@dataclass
class String:
    string: str
    pos: Pos        # Line, column, character index
    expr: List[Expression]  # Embedded GitHub expressions

# Usage in validation rules
def validate_context(self, string: String):
    if invalid_context:
        yield Problem(
            string.pos,  # Exact position for error reporting
            ProblemLevel.ERR,
            f"Unknown context: {string}",
            "expressions-contexts"
        )
```

### 3. Auto-Fixing System

Character-level edits for precise fixes:
```python
class Fixer:
    def edit_yaml_at_position(
        self, 
        char_index: int, 
        delete_count: int, 
        new_text: str, 
        problem: Problem,
        description: str
    ):
        # Apply character-exact fix to source file
```

### 4. Rule System Architecture

```python
class Rule(ABC):
    def __init__(self, workflow: Workflow, fixer: Fixer):
        self.workflow = workflow
        self.fixer = fixer
        
    @abstractmethod 
    def check(self) -> Generator[Problem, None, None]:
        # Yield problems found in workflow
        # Apply fixes through self.fixer if enabled
```

---

## 📝 Adding New Validation Rules

### 1. Create Rule Class
```python
# validate_actions/rules/my_new_rule.py
from validate_actions.rules.rule import Rule
from validate_actions.globals.problems import Problem, ProblemLevel

class MyNewRule(Rule):
    def check(self) -> Generator[Problem, None, None]:
        # Examine self.workflow AST
        for job in self.workflow.jobs.jobs:
            for step in job.steps.steps:
                if self._has_issue(step):
                    # Option 1: Report problem
                    yield Problem(
                        step.pos, 
                        ProblemLevel.ERR, 
                        "Description of issue",
                        "my-new-rule"
                    )
                    
                    # Option 2: Auto-fix if fixer available
                    if self.fixer:
                        self.fixer.edit_yaml_at_position(
                            step.pos.idx,
                            len("old_text"),  
                            "new_text",
                            problem,
                            "Fix description"
                        )
```

### 2. Register Rule
Add to `validate_actions/pipeline_stages/validator.py`:
```python
from validate_actions.rules.my_new_rule import MyNewRule

class ExtensibleValidator(IValidator):
    ACTIONS_ERROR_RULES = [
        ExpressionsContextsRule,
        JobsStepsUsesRule,
        StepsIOMatchRule,
        MyNewRule,  # Add your rule here
    ]
```

### 3. Add Tests
```python
# tests/rules_test/my_new_rule_test.py
def test_my_new_rule_detects_issue():
    workflow_yaml = """
    name: Test
    on: push
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - name: Bad Step
            run: echo "has issue"
    """
    
    problems = validate_yaml_content(workflow_yaml)
    assert len(problems.problems) == 1
    assert problems.problems[0].rule == "my-new-rule"
```

---

## 🔍 Debugging Tips

### VS Code Debugger Configuration
```json
// .vscode/launch.json
{
    "configurations": [
        {
            "name": "Debug validate-actions",
            "type": "debugpy",
            "request": "launch", 
            "program": "validate_actions/main.py",
            "args": ["tests/resources/warning_workflow.yml"],
            "console": "internalConsole",
            "justMyCode": false
        }
    ]
}
```

---

## 🧪 Testing Strategy
tbd

---

## 🚀 Release Process

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update version in `pyproject.toml` or `poetry version patch/minor/major`
- When PR is merged onto main, it triggers an automated release

---

## 🤝 Contributing Guidelines

### Contribution Workflow
1. **Fork** the repository
2. **Create** a feature branch (`feature/new-validation-rule`)
3. **Implement** changes with tests
4. **Run** the full test suite and quality checks
5. **Submit** a pull request with clear description

### Code Style Requirements
- **Black**: Code formatting (99 character line length)
- **isort**: Import sorting (Black-compatible profile)
- **Flake8**: Linting with line length 99
- **MyPy**: Type checking with strict settings
- **Docstrings**: Sphinx compatibility

### Commit Message Format

Follow conventional commits

### Pull Request Guidelines
- **Clear Title**: Descriptive summary of changes
- **Description**: What changes were made and why
- **Testing**: Evidence that changes work correctly
- **Documentation**: Updates to docs if needed
- **Breaking Changes**: Clearly marked if applicable

---

## 📚 Useful Resources

### GitHub Actions Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Context and Expression Syntax](https://docs.github.com/en/actions/learn-github-actions/contexts)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)

### Python Development Tools
- [Poetry](https://python-poetry.org/) - Dependency management
- [PyYAML](https://pyyaml.org/) - YAML processing
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [pytest](https://pytest.org/) - Testing framework

### Related Projects
- [actionlint](https://github.com/rhymond/actionlint) - Go-based GitHub Actions linter

---

Happy coding! 🎉