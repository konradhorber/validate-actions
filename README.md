# validate-actions

**Professional GitHub Actions workflow validation and linting from the CLI.**

Catch configuration errors, typos, and best practice violations in your GitHub Actions workflows before you push to production. Built for developers who want bulletproof CI/CD.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/validate-actions.svg)](https://badge.fury.io/py/validate-actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI
pip install validate-actions
```

### Basic Usage

```bash
# Validate all workflows in your repository
validate-actions

# Validate a specific workflow file
validate-actions .github/workflows/ci.yml

# Auto-fix issues where possible
validate-actions --fix

# More options
validate-actions --help
```

---

## 🏗️ What Gets Validated

### GitHub Actions Contexts
```yaml
# ✅ Valid context references
runs-on: ubuntu-latest
if: github.event_name == 'push'
env:
  BRANCH: ${{ github.ref_name }}

# ❌ Invalid context references (caught by validate-actions)
if: github.event.invalid_property  # Unknown property
env:
  USER: ${{ github.actor_name }}   # Should be github.actor
```

### Action Usage & Versions
```yaml
# ✅ Current action versions
- uses: actions/checkout@v4
- uses: actions/setup-node@v4
  with:
    node-version: '18'

# ❌ Outdated or incorrect usage (caught by validate-actions)  
- uses: actions/checkout@v2        # Outdated version
- uses: actions/setup-node@v4
  with:
    node_version: '18'             # Wrong input name
```

### Step Input/Output Dependencies
```yaml
# ✅ Proper step references
- id: build
  run: echo "artifact=my-app.zip" >> $GITHUB_OUTPUT
- name: Deploy
  run: deploy ${{ steps.build.outputs.artifact }}

# ❌ Invalid step references (caught by validate-actions)
- name: Deploy  
  run: deploy ${{ steps.invalid.outputs.artifact }}  # Step doesn't exist
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GH_TOKEN` | GitHub token for enhanced API rate limits | Optional |

### GitHub Token Setup
```bash
# For higher rate limits (heavy use)
export GH_TOKEN=ghp_your_token_here
validate-actions
```

A GitHub token enables:
- Higher API rate limits for action metadata fetching

### Extending Rules

validate-actions supports custom. You can extend the tool with your own rules without modifying the core codebase.

See [validate_actions/rules/rules.yml](validate_actions/rules/rules.yml) for configuration format and examples of creating custom rules.

---

## 🚦 Exit Codes

- **0**: Success (no errors, warnings under limit)
- **1**: Errors found OR warnings exceed `--max-warnings` limit

By default, warnings don't cause exit code 1 (non-blocking):
```bash
validate-actions              # Exit 0 even with warnings
validate-actions --quiet      # Exit 0, suppress warning output  
```

Use `--max-warnings` to fail builds when warnings exceed a threshold:
```bash
validate-actions --max-warnings 0    # Exit 1 on any warnings (strict)
validate-actions --max-warnings 5    # Exit 1 if more than 5 warnings
```

Perfect for CI/CD integration:
```yaml
# .github/workflows/validate.yml
- name: Validate Workflows (Allow Warnings)
  run: validate-actions
  # Will only fail on errors, not warnings
```

---

## 🏃‍♂️ Integration Examples

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-actions
        name: Validate GitHub Actions
        entry: validate-actions
        language: system
        files: ^\.github/workflows/.*\.ya?ml$
```

*Note: Requires `validate-actions` to be installed globally or available in your PATH. For poetry projects, consider using `entry: poetry run validate-actions`.*

### VS Code Task
```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Validate Actions",
      "type": "shell", 
      "command": "validate-actions",
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "always"
      }
    }
  ]
}
```

*Note: Assumes global installation (`pip install validate-actions`). For other setups, replace `command` with:*
- *Poetry: `"poetry run validate-actions"`*
- *Pipx: `"pipx run validate-actions"`*
- ...

### GitHub Actions Workflow
```yaml
# .github/workflows/validate.yml
name: Validate Workflows
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install validate-actions
      - name: Validate with warning limit
        run: validate-actions
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
*Note: Use `--max-warnings N` to set warning limits, or `--quiet` to suppress warning output entirely.*

---

## 🛠️ Development

See [DEV_README.md](DEV_README.md) for detailed development setup, architecture overview, and contribution guidelines.

### Quick Dev Setup with poetry
```bash
git clone https://github.com/konradhorber/validate-actions
cd validate-actions
poetry install --with dev
poetry run validate-actions
```

---

## 🤝 Contributing

We welcome contributions! Please see [DEV_README.md](DEV_README.md) for development setup and guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [PyYAML](https://pyyaml.org/) for robust YAML parsing
- [Typer](https://typer.tiangolo.com/) for the CLI interface
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [python-dotenv](https://github.com/theskumar/python-dotenv) for environment variable management  

Inspired by tools like ESLint and the GitHub Actions community's need for better workflow validation.