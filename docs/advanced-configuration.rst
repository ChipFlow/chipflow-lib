Advanced Configuration
======================

This guide covers advanced configuration options for ChipFlow projects, including customizing clock domains, debugging features, and platform-specific settings.

Advanced TOML Configuration
----------------------------

The ``chipflow.toml`` file supports many advanced configuration options beyond the basics covered in the getting started guide.

Clock Domains
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ChipFlow supports multiple clock domains in your design:

.. code-block:: toml

   [chipflow.clocks]
   # Default clock for the design
   default = "sys_clk"
   
   # Additional clock domains
   pll = "pll_clk"
   fast = "fast_clk"

Each named clock must have a corresponding pad defined in the pads section:

.. code-block:: toml

   [chipflow.silicon.pads]
   sys_clk = { type = "clock", loc = "N1" }
   pll_clk = { type = "clock", loc = "N2" }
   fast_clk = { type = "clock", loc = "N3" }

Debugging Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ChipFlow provides debugging options for silicon designs:

.. code-block:: toml

   [chipflow.silicon.debug]
   # Heartbeat LED to verify clock/reset functionality
   heartbeat = true
   
   # Internal logic analyzer
   logic_analyzer = true
   logic_analyzer_depth = 1024
   
   # JTAG debug access
   jtag = true

Pin Locking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To prevent pin assignments from changing accidentally, ChipFlow supports a pin locking mechanism:

.. code-block:: toml

   [chipflow.pin_lock]
   # Enable pin locking
   enabled = true
   
   # Lock file path (relative to project root)
   file = "pins.lock"

Once locked, pin assignments can only be changed by explicitly updating the lock file.

Resource Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For silicon designs, you can specify resource constraints:

.. code-block:: toml

   [chipflow.silicon.constraints]
   # Maximum die area in mm²
   max_area = 1.0
   
   # Maximum power budget in mW
   max_power = 100
   
   # Target clock frequency in MHz
   target_frequency = 100

Custom Top-Level Components
---------------------------

You can specify custom top-level components for your design:

.. code-block:: toml

   [chipflow.top]
   # Main SoC component
   soc = "my_design.components:MySoC"
   
   # Additional top-level components
   uart = "my_design.peripherals:UART"
   spi = "my_design.peripherals:SPI"

Each component should be a fully qualified Python path to a class that implements the Amaranth Component interface.

Platform-Specific Configuration
-------------------------------

Different target platforms may require specific configuration options:

FPGA Board Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: toml

   [chipflow.board]
   # Target FPGA board
   target = "ulx3s"
   
   # Board-specific options
   [chipflow.board.options]
   size = "85k"  # FPGA size
   spi_flash = true
   sdram = true

Silicon Process Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: toml

   [chipflow.silicon]
   # Target manufacturing process
   process = "gf130bcd"
   
   # Process-specific options
   [chipflow.silicon.options]
   metal_stack = "6LM"
   io_voltage = 3.3
   core_voltage = 1.2

External Dependencies
---------------------

ChipFlow can integrate with external dependencies:

.. code-block:: toml

   [chipflow.deps]
   # External IP cores
   cores = [
     "github.com/chipflow/uart-core@v1.0.0",
     "github.com/chipflow/spi-core@v2.1.0"
   ]
   
   # External library paths
   [chipflow.deps.libs]
   amaranth_cores = "amaranth_cores"
   chisel_cores = "chisel_cores"

Testing Configuration
---------------------

For more complex testing setups:

.. code-block:: toml

   [chipflow.sim]
   # Testbench implementation
   testbench = "my_design.tb:TestBench"
   
   # Custom simulation flags
   [chipflow.sim.options]
   trace_all = true
   cycles = 10000
   seed = 12345
   
   # Test vectors
   [chipflow.sim.test_vectors]
   path = "test_vectors.json"
   format = "json"

Documentation Configuration
---------------------------

To generate custom documentation for your design:

.. code-block:: toml

   [chipflow.docs]
   # Documentation output directory
   output = "docs/build"
   
   # Block diagram generation
   block_diagram = true
   
   # Custom templates
   template_dir = "docs/templates"
   
   # Additional documentation files
   extra_files = [
     "docs/architecture.md",
     "docs/api.md"
   ]

Environment Variables
---------------------

Several environment variables can be used to customize ChipFlow's behavior:

- ``CHIPFLOW_ROOT``: Root directory of your project
- ``CHIPFLOW_API_KEY_ID``: API key ID for ChipFlow services
- ``CHIPFLOW_API_KEY_SECRET``: API key secret for ChipFlow services
- ``CHIPFLOW_API_ENDPOINT``: Custom API endpoint (defaults to production)
- ``CHIPFLOW_DEBUG``: Enable debug logging (set to "1")
- ``CHIPFLOW_CONFIG``: Custom path to chipflow.toml file

Using Custom Steps
------------------

To implement a custom step implementation:

1. Create a new class that inherits from the base step:

   .. code-block:: python

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
              # ...

2. Reference your custom step in chipflow.toml:

   .. code-block:: toml

      [chipflow.steps]
      silicon = "my_design.custom_steps:CustomSiliconStep"

3. Your custom step will be used when invoking the corresponding command.

Advanced Pin Configurations
---------------------------

For complex pin requirements:

.. code-block:: toml

   [chipflow.silicon.pads]
   # Differential pair
   lvds_in_p = { type = "i", loc = "N4", diff_pair = "positive" }
   lvds_in_n = { type = "i", loc = "N5", diff_pair = "negative" }
   
   # Multiple bits of a bus
   data[0] = { type = "io", loc = "S1" }
   data[1] = { type = "io", loc = "S2" }
   data[2] = { type = "io", loc = "S3" }
   data[3] = { type = "io", loc = "S4" }
   
   # Special I/O modes
   spi_clk = { type = "o", loc = "E1", drive = "8mA", slew = "fast" }
   i2c_sda = { type = "io", loc = "W1", pull = "up", schmitt = true }

Integration with Version Control
--------------------------------

ChipFlow integrates with Git for version tracking:

1. Design submissions include Git commit hash for tracking
2. ChipFlow warns if submitting from a dirty Git tree
3. Version information is embedded in the manufacturing metadata

For CI/CD integration, set the following environment variables:

.. code-block:: bash

   # CI/CD environment variables
   export CHIPFLOW_CI=1
   export CHIPFLOW_NONINTERACTIVE=1
   
   # Authentication
   export CHIPFLOW_API_KEY_ID=your_ci_key_id
   export CHIPFLOW_API_KEY_SECRET=your_ci_key_secret