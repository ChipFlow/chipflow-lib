Creating Your First Project
---------------------------

1. Create a new directory for your project:

   .. code-block:: bash

      mkdir my-chipflow-project
      cd my-chipflow-project

2. Initialize your project:

   .. code-block:: bash

      pdm init
      pdm add chipflow-lib

3. Create a basic `chipflow.toml` configuration file:

   .. code-block:: toml

      [chipflow]
      project_name = "my-first-chip"

      [chipflow.clocks]
      default = "sys_clk"

      [chipflow.resets]
      default = "sys_rst_n"

      [chipflow.silicon]
      process = "gf130bcd"
      package = "pga144"

      [chipflow.silicon.debug]
      heartbeat = true

      [chipflow.silicon.pads]
      sys_clk   = { type = "clock", loc = "N1" }
      sys_rst_n = { type = "reset", loc = "N2" }

4. Create a simple design:

   Create a file called `design.py` with your hardware design. Here's a simple example:

   .. code-block:: python

      from amaranth import *
      from amaranth.lib.wiring import Component, In, Out

      class Blinky(Component):
          """A simple LED blinker"""

          def __init__(self):
              super().__init__()
              self.led = Out(1)

          def elaborate(self, platform):
              m = Module()

              # 24-bit counter (approx 1Hz with 16MHz clock)
              counter = Signal(24)
              m.d.sync += counter.eq(counter + 1)

              # Connect the counter's most significant bit to the LED
              m.d.comb += self.led.eq(counter[-1])

              return m

      class MyTop(Component):
          """Top-level design"""

          def __init__(self):
              super().__init__()
              self.blinky = Blinky()

          def elaborate(self, platform):
              m = Module()

              m.submodules.blinky = self.blinky

              # Wire up the blinky LED to an output pin
              led_out = platform.request("led")
              m.d.comb += led_out.eq(self.blinky.led)

              return m

Workflow Steps
--------------

ChipFlow organizes the design process into distinct steps:

1. **Simulation**: Test your design in a virtual environment
2. **Board**: Prepare your design for FPGA prototyping
3. **Silicon**: Prepare and submit your design for manufacturing

Each step is configured and executed through the ChipFlow CLI:

.. code-block:: bash

   # Simulate your design
   pdm chipflow sim prepare

   # Build for FPGA
   pdm chipflow board prepare

   # Prepare for silicon manufacturing
   pdm chipflow silicon prepare

   # Submit for manufacturing
   pdm chipflow silicon submit

Next Steps
----------

Now that you've created your first ChipFlow project, you can:

- Read the :doc:`workflows` guide to understand the detailed workflow
- Learn about the :doc:`chipflow-toml-guide` for configuring your project
- Explore :doc:`advanced-configuration` options

For more examples and detailed documentation, visit the `ChipFlow GitHub repository <https://github.com/ChipFlow/chipflow-lib>`_.
