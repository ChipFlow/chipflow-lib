# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

chipflow-lib is a Python library for working with the ChipFlow platform, enabling users to build ASIC (Application Specific Integrated Circuit) designs using the Amaranth HDL framework. The library provides a CLI tool (`chipflow`) that handles design elaboration, simulation, and submission to the ChipFlow cloud builder.

## Build and Test Commands

### Installation
- Install dependencies: `pdm install`
- Python 3.11+ required
- Uses PDM for dependency management

### Testing
- Run all tests: `pdm test`
- Run with coverage: `pdm test-cov`
- Run with HTML coverage report: `pdm test-cov-html`
- Run single test: `pdm run pytest tests/test_file.py::test_function_name`
- Run test for specific module with coverage: `pdm run python -m pytest --cov=chipflow_lib.MODULE tests/test_file.py -v`

### Linting
- Run all linting checks: `pdm lint`
  - Includes: license header check, ruff linting, and pyright type checking
- Run ruff only: `pdm run ruff check`
- Run pyright only: `pdm run pyright chipflow_lib`

### Documentation
- Build docs: `pdm docs`
- Test documentation: `pdm test-docs`

### Running the CLI
- Run chipflow CLI: `pdm chipflow <command>`

## High-Level Architecture

### Core Components

1. **CLI System** (`cli.py`):
   - Entry point for the `chipflow` command
   - Dynamically loads "steps" (silicon, sim, software) from configuration
   - Steps can be extended via `chipflow.toml` `[chipflow.steps]` section
   - Parses `chipflow.toml` configuration using Pydantic models

2. **Configuration System**:
   - `chipflow.toml`: User project configuration file (must exist in `CHIPFLOW_ROOT`)
   - `config_models.py`: Pydantic models defining configuration schema
   - `config.py`: Configuration file parsing logic
   - Key configuration sections: `[chipflow]`, `[chipflow.silicon]`, `[chipflow.simulation]`, `[chipflow.software]`, `[chipflow.test]`

3. **Platform Abstraction** (`platforms/`):
   - `SiliconPlatform`: Targets ASIC fabrication (supports SKY130, GF180, GF130BCD, IHP_SG13G2, HELVELLYN2)
   - `SimPlatform`: Targets simulation (builds C++ CXXRTL simulator)
   - `SoftwarePlatform`: RISC-V software build support
   - Each platform has process-specific port types (e.g., `Sky130Port` with drive mode configuration)

4. **Steps System** (`steps/`):
   - Extensible command architecture
   - `silicon.py`: Handles ASIC preparation and cloud submission
     - `prepare`: Elaborates Amaranth design to RTLIL
     - `submit`: Submits design to ChipFlow cloud builder (requires `CHIPFLOW_API_KEY`)
   - `sim.py`: Simulation workflow
     - `build`: Builds CXXRTL simulator
     - `run`: Runs simulation with software
     - `check`: Validates simulation against reference events
   - `software.py`: RISC-V software compilation

5. **Pin Locking System** (`_pin_lock.py`):
   - `chipflow pin lock`: Allocates physical pins for design components
   - Generates `pins.lock` file with persistent pin assignments
   - Attempts to reuse previous allocations when possible
   - Package definitions in `_packages.py` define available pins per package

6. **IO Annotations** (`platforms/_utils.py`, `platforms/_signatures.py`):
   - IO signatures define standard interfaces (JTAG, SPI, I2C, UART, GPIO, QSPI)
   - `IOModel` configures electrical characteristics (drive mode, trip point, inversion)
   - Annotations attach metadata to Amaranth components for automatic pin allocation

### Key Design Patterns

1. **Component Discovery via Configuration**:
   - User defines top-level components in `[chipflow.top]` section as `name = "module:ClassName"`
   - `_get_cls_by_reference()` dynamically imports and instantiates classes
   - `top_components()` returns dict of instantiated components

2. **Port Wiring**:
   - `_wire_up_ports()` in `steps/__init__.py` automatically connects platform ports to component interfaces
   - Uses pin lock data to map logical interface names to physical ports
   - Handles signal inversion, direction, and enable signals

3. **Build Process**:
   - Amaranth elaboration → RTLIL format → Yosys integration → Platform-specific output
   - For silicon: RTLIL sent to cloud builder with pin configuration
   - For simulation: RTLIL → CXXRTL C++ → compiled simulator executable

4. **Error Handling**:
   - Custom `ChipFlowError` exception for user-facing errors
   - Causes are preserved and printed with `traceback.print_exception(e.__cause__)`
   - CLI wraps unexpected exceptions in `UnexpectedError` with debug context

## Code Style

- Follow PEP-8 style
- Use `snake_case` for Python
- Type hints required (checked by pyright in standard mode)
- Ruff linting enforces: E4, E7, E9, F, W291, W293 (ignores F403, F405 for wildcard imports)
- All files must have SPDX license header: `# SPDX-License-Identifier: BSD-2-Clause`
- No trailing whitespace
- No whitespace on blank lines

## Testing Notes

- Tests located in `tests/` directory
- Fixtures in `tests/fixtures/`
- Use public APIs when testing unless specifically instructed otherwise
- CLI commands count as public API
- Test coverage enforced via pytest-cov

## Common Workflows

### Submitting a Design to ChipFlow Cloud
1. Create `chipflow.toml` with `[chipflow.silicon]` section defining process and package
2. Run `chipflow pin lock` to allocate pins
3. Run `chipflow silicon prepare` to elaborate design
4. Set `CHIPFLOW_API_KEY` environment variable
5. Run `chipflow silicon submit --wait` to submit and monitor build

### Running Simulation
1. Run `chipflow sim build` to build simulator
2. Run `chipflow sim run` to run simulation (builds software automatically)
3. Run `chipflow sim check` to validate against reference events (requires `[chipflow.test]` configuration)

## Environment Variables

- `CHIPFLOW_ROOT`: Project root directory (auto-detected if not set)
- `CHIPFLOW_API_KEY`: API key for cloud builder authentication
- `CHIPFLOW_API_KEY_SECRET`: Deprecated, use `CHIPFLOW_API_KEY` instead
- `CHIPFLOW_API_ORIGIN`: Cloud builder URL (default: https://build.chipflow.org)
- `CHIPFLOW_BACKEND_VERSION`: Developer override for backend version
- `CHIPFLOW_SUBMISSION_NAME`: Override submission name (default: git commit hash)
