# Ideas Extracted from Unfinished Documentation

This file contains useful ideas extracted from the unfinished documentation before it was removed.
These may be implemented in the future or serve as inspiration for documentation improvements.

## Good Ideas from advanced-configuration.rst

### Environment Variables (REAL - should be documented)
- `CHIPFLOW_ROOT`: Root directory of your project (must contain chipflow.toml)
- `CHIPFLOW_API_KEY`: API key for ChipFlow cloud services
- `CHIPFLOW_API_ENDPOINT`: Custom API endpoint (defaults to https://build.chipflow.com)
- `CHIPFLOW_DEBUG`: Enable debug logging (set to "1")

**Action**: Add environment variable reference to chipflow-commands.rst or chipflow-toml-guide.rst

### Custom Step Implementation Example (REAL - should be documented)
The doc had a good basic example:
```python
from chipflow_lib.steps.silicon import SiliconStep

class CustomSiliconStep(SiliconStep):
    def prepare(self):
        # Custom preparation logic
        result = super().prepare()
        # Additional processing
        return result

    def submit(self, rtlil_path, *, dry_run=False):
        # Custom submission logic
        if dry_run:
            # Custom dry run behavior
            return
        # Custom submission implementation
```

**Action**: Create dedicated "Customizing Steps" guide with real examples

### Git Integration Notes (REAL - worth mentioning)
- Design submissions include Git commit hash for tracking
- ChipFlow warns if submitting from a dirty Git tree
- Version information is embedded in manufacturing metadata

**Action**: Add to silicon workflow documentation

### CI/CD Integration (REAL)
- Use `CHIPFLOW_API_KEY` environment variable
- Standard CI secret handling practices apply

**Action**: Add brief CI/CD section to getting-started or create CI/CD guide

### Multiple Top-Level Components (REAL but needs clarification)
```toml
[chipflow.top]
soc = "my_design.components:MySoC"
uart = "my_design.peripherals:UART"
```

**Note**: This creates multiple top-level instances, NOT a hierarchy. Need to document what this actually does.

**Action**: Clarify [chipflow.top] behavior in chipflow-toml-guide.rst

## Aspirational Features (Not Implemented)

These were in the docs but don't exist in the codebase. Listed here in case they're planned for future:

### From advanced-configuration.rst:
- `[chipflow.clocks]` - Named clock domain configuration
- `[chipflow.silicon.debug]` - heartbeat, logic_analyzer, jtag options
- `[chipflow.silicon.constraints]` - max_area, max_power, target_frequency
- `[chipflow.deps]` - External IP core integration
- `[chipflow.docs]` - Automatic documentation generation
- `[chipflow.sim.options]` - trace_all, seed, custom cycles
- `[chipflow.sim.test_vectors]` - Test vector file support
- Advanced pad configurations - differential pairs, drive strength (8mA), slew rate, pull-up/down, schmitt trigger

### From workflows.rst:
- Board workflow / FPGA deployment (BoardStep doesn't exist)
- `chipflow silicon validate` command
- `chipflow silicon status` command
- Amaranth.sim-style testbenches (ChipFlow uses CXXRTL)
- VCD waveform dumping
- `[chipflow.board]` configuration section

### From create-project.rst:
- Project scaffolding / `pdm init` workflow
- `platform.request()` API pattern
- `[chipflow.resets]` configuration

## Why These Docs Were Removed

The unfinished docs contained too much aspirational content that:
1. Doesn't match the actual API/config schema
2. References unimplemented features
3. Could confuse users about what's real vs planned
4. Wasn't maintained as the codebase evolved

Better to have accurate documentation of what exists than aspirational docs of what might exist someday.

## What Was Kept

Good ideas from these docs have been incorporated into:
- `architecture.rst` - Overall system architecture
- `simulation-guide.rst` - Complete simulation workflow
- `using-pin-signatures.rst` - Pin configuration (the real way)
- Existing `chipflow-toml-guide.rst` and `chipflow-commands.rst`
