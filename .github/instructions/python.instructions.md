---
applyTo: '**'
---
Python execution guidelines:

- Always run Python scripts from the python_scripts directory.
  - cd python_scripts
- Use uv to execute scripts (do not call python or pip directly).
  - uv run <script.py> [args...]
  - Example: cd python_scripts && uv run main.py --help

Optional helpers:
- Add a dependency: uv add <package>
- Update lockfile (if used): uv lock
