# ChipFlow Library Development Guidelines

## Build & Test Commands
- Install dependencies: `pdm install`
- Run all tests: `pdm run test`
- Run a single test: `pdm run python -m pytest tests/test_file.py::test_function -v`
- Run tests with coverage: `pdm run test-cov`
- Run linting: `pdm run lint`
- Build documentation: `pdm run docs`
- Test documentation: `pdm run test-docs`

## Code Style Guidelines
- License header: Include `# SPDX-License-Identifier: BSD-2-Clause` at the top of each file
- Use type hints where appropriate (Python 3.10+ supported)
- Imports: Group standard library, third-party, and project imports with a blank line between groups
- Formatting: Project uses ruff (`F403`, `F405` are ignored)
- Naming: Use snake_case for functions/variables and PascalCase for classes
- Error handling: Custom errors inherit from `ChipFlowError`
- Documentation: Follow sphinx docstring format for public APIs
- Testing: Use pytest fixtures and assertions