# Package Pin Interface in chipflow-lib

This document describes the package pin interface in ChipFlow, introduced to provide a more structured and consistent way to specify pin configurations for chip packages.

## Overview

The package pin interface provides definitions for various types of pins in a chip package:

- Power and ground pins
- Clock pins
- Reset pins
- JTAG pins
- Heartbeat pins

Each package type (PGA, bare die, etc.) defines its own implementation of these pin types, with appropriate pin numbering and allocation strategies.

# Using the Package Pin Interface in Code

### Available Package Definitions

```python
from chipflow_lib.platforms import PACKAGE_DEFINITIONS

# Available package types
print(list(PACKAGE_DEFINITIONS.keys()))  # ['pga144', 'cf20', 'openframe']

# Get a package definition
package_def = PACKAGE_DEFINITIONS["pga144"]
print(package_def.name)          # "pga144"
print(package_def.package_type)  # "QuadPackageDef"
```

### Core Package Methods

```python
from chipflow_lib.platforms import PACKAGE_DEFINITIONS

package_def = PACKAGE_DEFINITIONS["pga144"]

# Allocate pins for components
# This method handles pin allocation logic for the package
pins = package_def.allocate_pins(component_requirements)

# Get bringup pins for testing/debugging
bringup_pins = package_def.bringup_pins()

# Register a component with the package
package_def.register_component(component)
```

### Working with Different Package Types

```python
from chipflow_lib.platforms import PACKAGE_DEFINITIONS

# Work with different package types
pga_package = PACKAGE_DEFINITIONS["pga144"]     # QuadPackageDef
cf_package = PACKAGE_DEFINITIONS["cf20"]        # BareDiePackageDef
openframe_package = PACKAGE_DEFINITIONS["openframe"]  # OpenframePackageDef

# Each package type has the same core interface
for name, package in PACKAGE_DEFINITIONS.items():
    print(f"{name}: {package.package_type}")
```

## Package Types

Currently available package types:

- **QuadPackageDef**: Used by `pga144` package
- **BareDiePackageDef**: Used by `cf20` package
- **OpenframePackageDef**: Used by `openframe` package

All package definitions implement the same core interface:
- `allocate_pins()`: Handle pin allocation logic
- `bringup_pins()`: Get pins for testing/debugging
- `register_component()`: Register components with the package

## Extending for New Package Types

To create a new package type, you need to:

1. Implement a new package definition class that provides the core methods
2. Add your new package type to the `PACKAGE_DEFINITIONS` dictionary

The new package definition should implement:
- `allocate_pins()` method for pin allocation
- `bringup_pins()` method for test pins
- `register_component()` method for component registration

## Running Tests

Tests for the package pin interface can be run using:

```bash
pdm run pytest tests/test_package_pins.py
```

## Available Packages

The current public API provides access to these packages through `PACKAGE_DEFINITIONS`:

- `pga144`: PGA-144 package (QuadPackageDef)
- `cf20`: CF-20 package (BareDiePackageDef)
- `openframe`: OpenFrame package (OpenframePackageDef)
