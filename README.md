# validate-actions 🚦

**Validate and lint your GitHub Actions workflows from the CLI.**
Make sure your workflows are clean, valid, and follow best practices — before you push.

---

## 🚀 Quickstart

Install globally with pip:

```bash
pip install -i https://test.pypi.org/simple/ validate-actions
```

Validate and lint your workflows (in project directory/subdirectory):

```bash
validate-actions
```

---

## 🛠️ Work with repo

Install poetry
```bash
pip install poetry
```

Install dependencies
```bash
poetry install --with dev
```

Run validate-actions
```bash
poetry run validate-actions
```

Debugger configuration in `.vscode/launch.json`
```json
"name": "Python Debugger: validateactions/main.py with Arguments",
"type": "debugpy",
"request": "launch",
"program": "validate_actions/main.py",
"console": "internalConsole",
"justMyCode": false,
```