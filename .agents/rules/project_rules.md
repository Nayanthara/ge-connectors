# Gemini Enterprise 3P Connectors - Project Rules & Guidelines

This document defines mandatory operational rules, architectural guidelines, and environment conventions for all AI agents and developers working in this repository.

## 1. Python Virtual Environment (`.venv`) Enforcement

* **Authoritative Virtual Environment Path**:
  * **MANDATORY**: Always use the dedicated virtual environment located at `.venv/` at the repository root (full path: `/home/user/connectors/ge-connectors/.venv`).
  * **Do not perform redundant research** on Python environment location—`.venv` at the repository root is the authoritative virtual environment containing all required project dependencies and dev tools (`pytest`, `ruff`, `flake8`).
  * Running Python binaries, linters, or test runners against system Python is strictly prohibited as required dependencies will be missing or cause environment drift.

* **Initialization & Setup Procedure**:
  * If `.venv` is missing, uninitialized, or dependencies are not installed, agents **MUST** initialize it before executing any Python tasks:
    ```bash
    # 1. Create the virtual environment if missing
    python3 -m venv .venv

    # 2. Activate and upgrade pip
    source .venv/bin/activate
    pip install --upgrade pip

    # 3. Install package and dev dependencies in editable mode
    pip install -e ".[dev]"
    ```

* **Execution Patterns**:
  When running Python scripts, tests, or linters, use one of the two approved patterns:

  * **Pattern A: Direct Path Invocation (Recommended for single tool calls)**
    ```bash
    # Run tests
    .venv/bin/pytest

    # Run specific test
    .venv/bin/pytest tests/test_catalog.py -k test_action_catalog_counts

    # Run linters
    .venv/bin/ruff check .
    .venv/bin/flake8 . --exclude=.venv

    # Run CLI tool
    .venv/bin/python ge_connector_tool.py --help
    ```

  * **Pattern B: Source Activation (Recommended for chained or interactive commands)**
    ```bash
    source .venv/bin/activate && pytest
    source .venv/bin/activate && python ge_connector_tool.py --help
    source .venv/bin/activate && ruff check .
    ```

---

## 2. Contrastive Execution Rules

### ❌ Incorrect (Anti-patterns - Do NOT do this)
```bash
# Anti-pattern: Running pytest globally (fails: pytest is not in system PATH or lacks dependencies)
pytest

# Anti-pattern: Running python3 directly from system
python3 ge_connector_tool.py --help

# Anti-pattern: Running linters without virtual environment context
ruff check .
flake8 .
```

### ✅ Correct (Approved patterns - Do this)
```bash
# Correct: Invoking pytest directly via .venv
.venv/bin/pytest

# Correct: Activating .venv in command chain
source .venv/bin/activate && pytest

# Correct: Invoking Python scripts with .venv interpreter
.venv/bin/python ge_connector_tool.py --help

# Correct: Invoking linters via .venv
.venv/bin/ruff check .
.venv/bin/flake8 . --exclude=.venv
```

---

## 3. Testing & Quality Standards

* **Python Unit Tests (`tests/`)**:
  * Always execute with `.venv/bin/pytest` or `source .venv/bin/activate && pytest`.
  * Ensure all 17+ tests pass before submitting changes or completing tasks.
* **Python Linting**:
  * Ruff: `.venv/bin/ruff check .`
  * Flake8: `.venv/bin/flake8 . --exclude=.venv`
* **Terraform Validation & Testing**:
  * Format check: `terraform fmt -check -diff -recursive terraform_templates/`
  * Module test: `terraform -chdir=terraform_templates/entra-connector test`
  * App test: `terraform -chdir=terraform_templates/azure-entra-app test`
