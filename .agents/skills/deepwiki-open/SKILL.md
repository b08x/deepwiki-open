```markdown
# deepwiki-open Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the development patterns and conventions used in the `deepwiki-open` Python codebase. You'll learn about file naming, import/export styles, commit patterns, and how to structure and run tests. This guide will help you contribute code that matches the project's established style and workflows.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `data_loader.py`, `wiki_parser.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import clean_text
    from .models import WikiEntry
    ```

### Export Style
- Use **named exports** (explicitly define what is exported).
  - Example:
    ```python
    __all__ = ['WikiEntry', 'parse_article']
    ```

### Commit Patterns
- Commit messages are **freeform** with occasional `feature` prefixes.
- Average commit message length: **73 characters**.
  - Example: `feature: add basic article parsing and cleaning logic`

## Workflows

### Adding a New Feature
**Trigger:** When you want to implement a new capability or module.
**Command:** `/add-feature`

1. Create a new Python file using snake_case naming.
2. Implement your feature using relative imports for any internal dependencies.
3. Add named exports to the new file (update `__all__` if appropriate).
4. Write corresponding test files using the `*.test.*` pattern.
5. Commit your changes with a descriptive message, optionally prefixed with `feature`.
6. Push your branch and open a pull request.

### Writing and Running Tests
**Trigger:** When you need to verify new or existing functionality.
**Command:** `/run-tests`

1. Create test files following the pattern `*.test.*` (e.g., `parser.test.py`).
2. Write tests for all public functions and classes.
3. Use the project's chosen (unknown) test framework—check existing test files for clues.
4. Run tests locally to ensure all pass before pushing changes.

### Refactoring Code
**Trigger:** When improving code structure or readability without changing behavior.
**Command:** `/refactor`

1. Identify code to refactor, ensuring file naming and import styles remain consistent.
2. Update relative imports as needed.
3. Update named exports if you change public APIs.
4. Run all tests to confirm nothing is broken.
5. Commit with a clear message describing the refactor.

## Testing Patterns

- Test files use the `*.test.*` naming convention (e.g., `module.test.py`).
- The specific test framework is **unknown**; check existing tests for syntax and structure.
- Place tests alongside or near the modules they test.
- Example test file structure:
    ```python
    # parser.test.py
    from .parser import parse_article

    def test_parse_article_basic():
        article = "Sample text"
        result = parse_article(article)
        assert result is not None
    ```

## Commands
| Command        | Purpose                                             |
|----------------|-----------------------------------------------------|
| /add-feature   | Start the process of adding a new feature/module    |
| /run-tests     | Run all test files to verify code correctness       |
| /refactor      | Begin a code refactor while preserving conventions  |
```
