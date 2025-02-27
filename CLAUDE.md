# AI-Gijiroku Development Guide

## Commands

### Testing
- Run all tests: `python -m pytest tests/test_*.py -v`
- Run single test file: `python -m pytest tests/path/to/test_file.py -v`
- Run specific test: `python -m pytest tests/path/to/test_file.py::TestClass::test_method -v`

### Application
- Record audio: `python src/main.py record`
- Transcribe audio: `python src/main.py transcribe -f path/to/audio.wav`
- Extract TODOs: `python src/main.py extract-todos path/to/transcript.txt`

## Code Style

### Imports
- Standard library imports first
- Third-party imports second
- Local module imports last

### Naming Conventions
- `snake_case` for functions and variables
- `PascalCase` for classes
- Japanese docstrings in triple quotes

### Error Handling
- Use explicit try/except blocks with clear error messages
- Log errors properly and provide user-friendly messages

### Testing
- Use pytest as testing framework
- Use unittest.mock for mocking dependencies
- Follow TDD best practices