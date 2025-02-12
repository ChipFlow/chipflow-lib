# Package Pin Interface in ChipFlow

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

### Getting Default Pins

```python
from chipflow_lib.platforms.utils import PACKAGE_DEFINITIONS, PowerType, JTAGWireName

# Get a package definition
package_def = PACKAGE_DEFINITIONS["pga144"]

# Get power pins
power_pins = package_def.power
vdd_pin = power_pins[PowerType.POWER]  # Get the default power pin
gnd_pin = power_pins[PowerType.GROUND]  # Get the default ground pin

# Get clock pins
clock_pins = package_def.clocks
default_clock = clock_pins[0]  # Get the first clock pin

# Get JTAG pins
jtag_pins = package_def.jtag
tck_pin = jtag_pins[JTAGWireName.TCK]  # Get the TCK pin
tms_pin = jtag_pins[JTAGWireName.TMS]  # Get the TMS pin
```

### Creating a Package with Default Pins

```python
from chipflow_lib.platforms.utils import PACKAGE_DEFINITIONS

# Create a package with a specific package definition
package = Package(package_type=PACKAGE_DEFINITIONS["pga144"])

# Initialize default pins from the package definition
package.initialize_from_package_type()
```

## Extending for New Package Types

To create a new package type, you need to:

1. Subclass `_BasePackageDef` and implement all the required properties and methods
2. Add your new package type to the `PackageDef` union and `PACKAGE_DEFINITIONS` dictionary

Example:

```python
class MyNewPackageDef(_BasePackageDef):
    type: Literal["MyNewPackageDef"] = "MyNewPackageDef"
    # ... implement all required methods ...

# Add to the union
PackageDef = Union[_QuadPackageDef, _BareDiePackageDef, MyNewPackageDef, _BasePackageDef]

# Add to the dictionary of available packages
PACKAGE_DEFINITIONS["my_new_package"] = MyNewPackageDef(name="my_new_package", ...)
```

## Running Tests

Tests for the package pin interface can be run using:

```bash
pdm run pytest tests/test_package_pins.py
```
