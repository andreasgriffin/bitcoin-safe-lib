# Agent Guidelines

- Never use `getattr` or `setattr`;
- use type hints
- write clean code.  if you're writing many if statements you're probably doing it wrong. Less code is better to understand the logic and to reduce bugs.
- modularize behavior into the most relevant class/module; do not centralize unrelated functionality in one class.
- avoid keyword-only `*` in method/function signatures unless explicitly requested.
- Before you commit, run pre-commit ruff format. commit and push the changes (use a dedicated branch for each session). If the pre-commit returns errors, fix them. For the pre-commit to work you have to cd into the current project and activate the environment.
- Ensure git hooks can resolve `python`: run commit/pre-commit commands with the project venv first on `PATH`, e.g. `PATH="$(poetry env info -p)/bin:$PATH" poetry run pre-commit run ruff-format --files <files>` and `PATH="$(poetry env info -p)/bin:$PATH" git commit -m "<message>"`.
- run relevant pytests
