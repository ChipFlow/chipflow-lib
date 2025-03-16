ChipFlow Workflows
==================

This guide details the different workflows available in the ChipFlow platform, from simulation to silicon manufacturing.

Overview
--------

ChipFlow organizes the IC design process into several logical steps, each addressing a different phase of development:

1. **Simulation**: Virtual testing of your design
2. **Board**: FPGA prototyping
3. **Silicon**: Manufacturing preparation and submission

Each workflow is implemented as a "step" in the ChipFlow library and can be accessed through the CLI tool.

Simulation Workflow
--------------------

The simulation workflow allows you to test your design in a virtual environment before committing to hardware.

**Commands:**

.. code-block:: bash

   # Prepare the simulation environment
   python -m chipflow_lib.cli sim prepare

   # Run the simulation tests
   python -m chipflow_lib.cli sim run

**Key Configuration:**

In your chipflow.toml file, you can specify simulation-specific settings:

.. code-block:: toml

   [chipflow.sim]
   # Test-bench top module
   testbench = "my_design.tb:TestBench"

   # Simulation duration in clock cycles
   cycles = 10000

   # Optional VCD waveform dump file
   vcd = "sim.vcd"

**Building a Test Bench:**

Create a test bench file (e.g., `tb.py`) with a class that implements the simulation logic:

.. code-block:: python

   from amaranth import *
   from amaranth.sim import Simulator
   from my_design import MyDesign

   class TestBench:
       def __init__(self):
           self.dut = MyDesign()
           
       def elaborate(self, platform):
           m = Module()
           m.submodules.dut = self.dut
           
           # Add stimulus logic here
           
           return m
           
       def sim_traces(self):
           # Return signals to trace in simulation
           return [self.dut.clk, self.dut.reset, self.dut.output]
           
       def sim_test(self, sim):
           # Stimulus generation
           def process():
               # Reset the design
               yield self.dut.reset.eq(1)
               yield Tick()
               yield self.dut.reset.eq(0)
               
               # Run test vectors
               for i in range(100):
                   yield self.dut.input.eq(i)
                   yield Tick()
                   output = yield self.dut.output
                   print(f"Input: {i}, Output: {output}")
                   
           sim.add_process(process)

Board Workflow
----------------

The board workflow prepares your design for FPGA deployment, which is useful for prototyping before committing to silicon.

**Commands:**

.. code-block:: bash

   # Prepare the design for FPGA deployment
   python -m chipflow_lib.cli board prepare

   # Deploy to FPGA
   python -m chipflow_lib.cli board deploy

**Key Configuration:**

.. code-block:: toml

   [chipflow.board]
   # Target FPGA board
   target = "tangnano9k"  # or "icebreaker", "ulx3s", etc.

   # Pin mappings for your design
   [chipflow.board.pins]
   clk = "CLK"
   reset = "BTN1"
   leds[0] = "LED1"
   leds[1] = "LED2"

Silicon Workflow
-----------------

The silicon workflow is the path to producing actual ASICs through ChipFlow's manufacturing services.

**Commands:**

.. code-block:: bash

   # Prepare design for manufacturing
   python -m chipflow_lib.cli silicon prepare

   # Validate the design against manufacturing rules
   python -m chipflow_lib.cli silicon validate

   # Submit the design for manufacturing
   python -m chipflow_lib.cli silicon submit

   # Check the status of a submitted design
   python -m chipflow_lib.cli silicon status

**Key Configuration:**

The silicon workflow requires detailed configuration in your chipflow.toml file:

.. code-block:: toml

   [chipflow.silicon]
   # Target manufacturing process
   process = "gf130bcd"

   # Physical package for the chip
   package = "cf20"

   # Optional debugging features
   [chipflow.silicon.debug]
   heartbeat = true

   # Pin assignments
   [chipflow.silicon.pads]
   sys_clk = { type = "clock", loc = "N1" }
   sys_rst_n = { type = "reset", loc = "N2" }
   led = { type = "o", loc = "N3" }

   # Power connections
   [chipflow.silicon.power]
   vdd = { type = "power", loc = "E1" }
   vss = { type = "ground", loc = "E2" }

**Submission Process:**

When submitting a design for manufacturing:

1. ChipFlow validates your design against process design rules
2. The design is converted to the necessary formats for manufacturing
3. You receive a quote and timeline for production
4. Once approved, the design enters the manufacturing queue
5. You receive updates on the progress of your chip

Authentication for Submission
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To submit a design, you'll need to set up authentication:

1. Create a `.env` file in your project directory with your API keys:

   .. code-block:: bash

      CHIPFLOW_API_KEY_ID=your_key_id
      CHIPFLOW_API_KEY_SECRET=your_key_secret

2. Alternatively, set these as environment variables before submission:

   .. code-block:: bash

      export CHIPFLOW_API_KEY_ID=your_key_id
      export CHIPFLOW_API_KEY_SECRET=your_key_secret
      python -m chipflow_lib.cli silicon submit

Customizing Workflows
---------------------

You can customize any workflow by creating your own implementation of the standard steps:

.. code-block:: toml

   [chipflow.steps]
   # Custom implementation of the silicon step
   silicon = "my_design.steps.silicon:MySiliconStep"

   # Custom implementation of the simulation step
   sim = "my_design.steps.sim:MySimStep"

Your custom step class should inherit from the corresponding base class in `chipflow_lib.steps` and override the necessary methods.

Next Steps
----------

- Learn about :doc:`advanced-configuration` options
- Explore the :doc:`chipflow-toml-guide` for detailed configuration options
- See API documentation for :doc:`autoapi/steps/index` to create custom workflow steps
