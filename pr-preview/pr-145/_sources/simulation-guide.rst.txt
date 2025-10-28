Simulation Guide
================

This guide explains how to use ChipFlow's simulation system to test your designs before committing to silicon.

Overview
--------

ChipFlow uses CXXRTL (C++ RTL simulation) to create fast, compiled simulations of your designs. The simulation system:

1. Converts your Amaranth design to CXXRTL C++ code
2. Automatically instantiates C++ models for your peripherals (UART, SPI flash, GPIO)
3. Compiles everything into a standalone executable
4. Runs your firmware on the simulated SoC

This allows cycle-accurate testing with real firmware, interactive debugging, and automated integration testing.

Basic Workflow
--------------

The typical simulation workflow:

.. code-block:: bash

    # Lock pins (required before simulation)
    pdm run chipflow pin lock

    # Build the simulation
    pdm run chipflow sim build

    # Run the simulation
    pdm run chipflow sim run

    # Run simulation and check against reference
    pdm run chipflow sim check

What Happens During Simulation
-------------------------------

1. **Design Elaboration**

   ChipFlow elaborates your design and extracts:

   - Top-level I/O signatures (UART, GPIO, SPI, etc.)
   - Pin assignments from ``pins.lock``
   - Software binaries to load (from ``attach_data()``)
   - Peripheral metadata (from ``SoftwareDriverSignature``)

2. **CXXRTL Code Generation**

   Amaranth converts your design to C++ using CXXRTL:

   .. code-block:: text

       design.py → Fragment → RTLIL → CXXRTL C++ → sim_soc.cc

3. **Model Instantiation**

   For each interface with a ``SimInterface`` annotation, ChipFlow:

   - Looks up the corresponding C++ model (uart_model, spiflash_model, etc.)
   - Generates code to instantiate and wire it up
   - Configures the model based on signature parameters

4. **Main.cc Generation**

   ChipFlow generates ``main.cc`` that:

   - Instantiates your design (``p_sim__top``)
   - Instantiates peripheral models
   - Sets up the CXXRTL debugger agent
   - Loads software binaries into flash models
   - Runs the clock for the configured number of steps

5. **Compilation**

   Everything is compiled together using Zig as the C++ compiler:

   .. code-block:: bash

       zig c++ -O3 -g -std=c++17 \\
           sim_soc.cc main.cc models.cc \\
           -o sim_soc

6. **Execution**

   The resulting ``sim_soc`` executable runs your design.

SimPlatform Internals
---------------------

The ``SimPlatform`` class is responsible for managing the simulation build process.

Automatic Model Matching
~~~~~~~~~~~~~~~~~~~~~~~~~

ChipFlow includes built-in models for common peripherals:

.. code-block:: python

    # From chipflow_lib/platform/sim.py
    _COMMON_BUILDER = BasicCxxBuilder(
        models=[
            SimModel('spi', 'chipflow::models', SPISignature),
            SimModel('spiflash', 'chipflow::models', QSPIFlashSignature, [SimModelCapability.LOAD_DATA]),
            SimModel('uart', 'chipflow::models', UARTSignature),
            SimModel('i2c', 'chipflow::models', I2CSignature),
            SimModel('gpio', 'chipflow::models', GPIOSignature),
        ],
        ...
    )

When you use ``UARTSignature()`` in your design, SimPlatform automatically:

1. Extracts the ``SimInterface`` annotation with UID ``"com.chipflow.chipflow_lib.UARTSignature"``
2. Looks up the model in ``_COMMON_BUILDER._table``
3. Generates: ``chipflow::models::uart uart_0("uart_0", top.p_uart__0____tx____o, top.p_uart__0____rx____i)``

Port Instantiation
~~~~~~~~~~~~~~~~~~

SimPlatform creates ``SimulationPort`` objects for each pin in your design:

.. code-block:: python

    # Inside SimPlatform.instantiate_ports()
    for name, port_desc in interface_desc.items():
        self._ports[port_desc.port_name] = io.SimulationPort(
            port_desc.direction,
            port_desc.width,
            invert=port_desc.invert,
            name=port_desc.port_name
        )

These ports become the top-level I/O of your simulated design.

Clock and Reset Handling
~~~~~~~~~~~~~~~~~~~~~~~~~

Clocks and resets receive special treatment:

- **Clocks**: Connected to Amaranth ``ClockDomain``
- **Resets**: Synchronized with ``FFSynchronizer`` for proper reset behavior

.. code-block:: python

    # Clock domain creation
    setattr(m.domains, domain, ClockDomain(name=domain))
    clk_buffer = io.Buffer(clock.direction, self._ports[clock.port_name])
    m.d.comb += ClockSignal().eq(clk_buffer.i)

    # Reset synchronization
    rst_buffer = io.Buffer(reset.direction, self._ports[reset.port_name])
    ffsync = FFSynchronizer(rst_buffer.i, ResetSignal())

Generated main.cc
~~~~~~~~~~~~~~~~~

The generated ``main.cc`` follows this structure:

.. code-block:: cpp

    #include <cxxrtl/cxxrtl.h>
    #include <cxxrtl/cxxrtl_server.h>
    #include "sim_soc.h"
    #include "models.h"

    int main(int argc, char **argv) {
        // Instantiate design
        p_sim__top top;

        // Instantiate peripheral models
        chipflow::models::spiflash flash("flash", top.p_flash____clk____o, ...);
        chipflow::models::uart uart_0("uart_0", top.p_uart__0____tx____o, ...);
        chipflow::models::gpio gpio_0("gpio_0", top.p_gpio__0____gpio____o, ...);

        // Set up debugger
        cxxrtl::agent agent(cxxrtl::spool("spool.bin"), top);
        if (getenv("DEBUG"))
            std::cerr << "Waiting for debugger on " << agent.start_debugging() << std::endl;

        // Set up event logging
        open_event_log("events.json");

        // Clock tick function
        auto tick = [&]() {
            flash.step(timestamp);
            uart_0.step(timestamp);
            gpio_0.step(timestamp);

            top.p_clk.set(false);
            agent.step();
            agent.advance(1_us);
            ++timestamp;

            top.p_clk.set(true);
            agent.step();
            agent.advance(1_us);
            ++timestamp;
        };

        // Load software
        flash.load_data("../software/software.bin", 0x00100000U);

        // Reset sequence
        top.p_rst.set(true);
        tick();
        top.p_rst.set(false);

        // Run simulation
        for (int i = 0; i < num_steps; i++)
            tick();

        close_event_log();
        return 0;
    }

Configuration
-------------

chipflow.toml Settings
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: toml

    [chipflow.simulation]
    # Number of clock cycles to simulate (default: 3000000)
    num_steps = 3000000

    [chipflow.test]
    # Reference event log for integration testing
    event_reference = "design/tests/events_reference.json"

Simulation Commands
-------------------

chipflow sim build
~~~~~~~~~~~~~~~~~~

Builds the simulation executable:

1. Elaborates the design
2. Generates CXXRTL C++
3. Generates main.cc
4. Compiles to ``build/sim/sim_soc``

chipflow sim run
~~~~~~~~~~~~~~~~

Runs the simulation:

1. Builds software (if needed)
2. Builds simulation (if needed)
3. Executes ``build/sim/sim_soc``

Output appears in the terminal, and ``events.json`` is written to ``build/sim/``.

chipflow sim check
~~~~~~~~~~~~~~~~~~

Runs simulation and validates output:

1. Runs ``chipflow sim run``
2. Compares ``build/sim/events.json`` against reference
3. Reports pass/fail

Useful for regression testing in CI/CD.

Debugging with RTL Debugger
----------------------------

ChipFlow simulations integrate with the `RTL Debugger <https://github.com/amaranth-lang/rtl-debugger>`_ VS Code extension.

Enable Debugging
~~~~~~~~~~~~~~~~

.. code-block:: bash

    DEBUG=1 pdm run chipflow sim run

This starts the CXXRTL debug server and prints:

.. code-block:: text

    Waiting for debugger on localhost:37268

.. Attach Debugger
   ~~~~~~~~~~~~~~~

   1. Install the RTL Debugger extension in VS Code
   2. Open the command palette (Cmd+Shift+P / Ctrl+Shift+P)
   3. Run "RTL Debugger: Connect to CXXRTL Server"
   4. Enter the host:port from the simulation output

   You can now:

   - View signal values in real-time
   - Set breakpoints on signal conditions
   - Step through clock cycles
   - Inspect design hierarchy

Event Logging for Testing
--------------------------

Peripheral models can log events to ``events.json`` for automated testing.

Logging Events
~~~~~~~~~~~~~~

UART model automatically logs received characters:

.. code-block:: json

    [
      {"type": "uart_rx", "data": "H", "timestamp": 1234},
      {"type": "uart_rx", "data": "e", "timestamp": 1256},
      {"type": "uart_rx", "data": "l", "timestamp": 1278},
      {"type": "uart_rx", "data": "l", "timestamp": 1300},
      {"type": "uart_rx", "data": "o", "timestamp": 1322}
    ]

Creating Reference
~~~~~~~~~~~~~~~~~~

1. Run simulation and capture good output:

   .. code-block:: bash

       pdm run chipflow sim run
       cp build/sim/events.json design/tests/events_reference.json

2. Configure in ``chipflow.toml``:

   .. code-block:: toml

       [chipflow.test]
       event_reference = "design/tests/events_reference.json"

3. Use in testing:

   .. code-block:: bash

       pdm run chipflow sim check

Input Commands (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can provide input commands via ``design/tests/input.json``. To reduce test churn from timing changes, input files use output events as triggers rather than timestamps:

.. code-block:: json

    {
      "commands": [
        {"type": "action", "peripheral": "uart_0", "event": "tx", "payload": 72},
        {"type": "wait", "peripheral": "uart_0", "event": "tx", "payload": 62},
        {"type": "action", "peripheral": "uart_0", "event": "tx", "payload": 10}
      ]
    }

Commands are processed sequentially:

- ``action`` commands queue an action (like transmitting data) for a peripheral
- ``wait`` commands pause execution until the specified event occurs

See the `mcu_soc example <https://github.com/ChipFlow/chipflow-examples/blob/main/mcu_soc/design/tests/input.json>`_ for a working input.json file.

Customizing Simulation
----------------------

Adding Custom Models
~~~~~~~~~~~~~~~~~~~~

ChipFlow's built-in simulation models cover common peripherals (UART, SPI, I2C, GPIO, QSPI Flash). For custom peripherals, you'll need to write C++ models that interact with the CXXRTL-generated design.

.. warning::
   The custom simulation model interface is subject to change. Model APIs may be updated in future ChipFlow releases. Built-in models (UART, SPI, etc.) are stable, but custom model registration and integration mechanisms may evolve.

**Learning Resources:**

1. **Study existing models**: The best way to learn is to examine ChipFlow's built-in implementations:

   - ``chipflow_lib/common/sim/models.h`` - Model interfaces and helper functions
   - ``chipflow_lib/common/sim/models.cc`` - Complete implementations for:

     - ``uart`` - UART transceiver with baud rate control
     - ``spiflash`` - QSPI flash memory with command processing
     - ``spi`` - Generic SPI peripheral
     - ``i2c`` - I2C bus controller with start/stop detection

2. **CXXRTL Runtime API**: Models interact with the generated design using CXXRTL's API:

   - `CXXRTL Documentation <https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/write_cxxrtl.html>`_ - Command reference
   - CXXRTL runtime source: ``yosys/backends/cxxrtl/runtime/`` (in Yosys repository)
   - Key types: ``cxxrtl::value<WIDTH>`` for signal access, ``.get()`` to read, ``.set()`` to write

**Model Registration:**

Once you've written a model (e.g., ``design/sim/my_model.h``), register it with ChipFlow:

.. code-block:: python

    from chipflow_lib.platform import SimPlatform, SimModel, BasicCxxBuilder
    from pathlib import Path

    MY_BUILDER = BasicCxxBuilder(
        models=[
            SimModel('my_peripheral', 'my_design', MyPeripheralSignature),
        ],
        hpp_files=[Path('design/sim/my_model.h')],
    )

    class MySimStep(SimStep):
        def __init__(self, config):
            super().__init__(config)
            self.platform._builders.append(MY_BUILDER)

Then reference your custom step in ``chipflow.toml``:

.. code-block:: toml

    [chipflow.steps]
    sim = "my_design.steps.sim:MySimStep"

.. note::
   Comprehensive CXXRTL runtime documentation is planned for a future release. For now, refer to existing model implementations and the Yosys CXXRTL source code.

Performance Tips
----------------

1. **Reduce sim cycles**: Lower ``num_steps`` during development

   .. code-block:: toml

       [chipflow.simulation]
       num_steps = 100000  # Instead of 3000000

2. **Use Release builds**: Already enabled by default (``-O3``)

3. **Disable debug server**: Don't set ``DEBUG=1`` unless actively debugging

4. **Profile your design**: Use the RTL Debugger to find bottlenecks in your HDL

Common Issues
-------------

Incomplete Simulation Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: Simulation completes but expected operations are incomplete

**Note**: The simulation will always stop after ``num_steps`` clock cycles, regardless of what the design or software is doing. If your firmware hasn't completed by then, you'll see incomplete output.

**Causes**:
- ``num_steps`` too low for the operations being performed
- Firmware stuck in infinite loop
- Waiting for peripheral that never responds

**Solutions**:
- Increase ``num_steps`` in chipflow.toml if legitimate operations need more time
- Enable ``DEBUG=1`` and attach debugger to see where execution is stuck
- Add timeout checks in your firmware to detect hangs
- Use event logging to see how far the simulation progressed

No UART Output
~~~~~~~~~~~~~~

**Symptom**: Expected UART output doesn't appear

**Causes**:
- UART baud rate misconfigured
- UART peripheral not initialized
- Software not running

**Solutions**:
- Check ``init_divisor`` matches clock frequency
- Verify UART initialization in firmware
- Check that flash model loaded software correctly

Model Not Found
~~~~~~~~~~~~~~~

**Symptom**: ``Unable to find a simulation model for 'com.chipflow.chipflow_lib.XXX'``

**Causes**:
- Using a signature without a corresponding model
- Custom signature not registered in a builder

**Solutions**:
- Use built-in signatures (UART, GPIO, SPI, I2C, QSPIFlash)
- Or create a custom model and register it with a ``BasicCxxBuilder``

Example: Complete Simulation Setup
-----------------------------------

Here's a complete example showing simulation setup for a simple SoC:

Design (design/design.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from amaranth import Module
    from amaranth.lib.wiring import Component, Out, connect, flipped
    from amaranth_soc import csr

    from chipflow_digital_ip.io import UARTPeripheral, GPIOPeripheral
    from chipflow_digital_ip.memory import QSPIFlash
    from chipflow_lib.platforms import (
        UARTSignature, GPIOSignature, QSPIFlashSignature,
        attach_data, SoftwareBuild
    )

    class MySoC(Component):
        def __init__(self):
            super().__init__({
                "flash": Out(QSPIFlashSignature()),
                "uart": Out(UARTSignature()),
                "gpio": Out(GPIOSignature(pin_count=4)),
            })
            self.bios_offset = 0x100000

        def elaborate(self, platform):
            m = Module()

            # CSR decoder
            csr_decoder = csr.Decoder(addr_width=28, data_width=8)
            m.submodules.csr_decoder = csr_decoder

            # Flash
            m.submodules.flash = flash = QSPIFlash()
            csr_decoder.add(flash.csr_bus, name="flash", addr=0x00000000)
            connect(m, flipped(self.flash), flash.pins)

            # UART
            m.submodules.uart = uart = UARTPeripheral(init_divisor=217)
            csr_decoder.add(uart.bus, name="uart", addr=0x02000000)
            connect(m, flipped(self.uart), uart.pins)

            # GPIO
            m.submodules.gpio = gpio = GPIOPeripheral(pin_count=4)
            csr_decoder.add(gpio.bus, name="gpio", addr=0x01000000)
            connect(m, flipped(self.gpio), gpio.pins)

            # Attach software
            from pathlib import Path
            sw = SoftwareBuild(
                sources=Path('design/software').glob('*.c'),
                offset=self.bios_offset
            )
            attach_data(self.flash, flash, sw)

            return m

Configuration (chipflow.toml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: toml

    [chipflow]
    project_name = "my_soc"
    clock_domains = ["sync"]

    [chipflow.top]
    soc = "design.design:MySoC"

    [chipflow.silicon]
    process = "sky130"
    package = "pga144"

    [chipflow.simulation]
    num_steps = 1000000

    [chipflow.test]
    event_reference = "design/tests/events_reference.json"

Firmware (design/software/main.c)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    #include "soc.h"

    int main() {
        // UART is auto-initialized by attach_data

        // Print test message
        puts("Hello from ChipFlow simulation!");

        // Blink GPIO
        for (int i = 0; i < 10; i++) {
            UART->gpio_data = i & 0xF;
        }

        return 0;
    }

Running
~~~~~~~

.. code-block:: bash

    # Lock pins
    pdm run chipflow pin lock

    # Run simulation
    pdm run chipflow sim run

Expected output:

.. code-block:: text

    Building simulation...
    Building software...
    🐱: nyaa~!
    Hello from ChipFlow simulation!

See Also
--------

- :doc:`architecture` - Overall ChipFlow architecture
- :doc:`using-pin-signatures` - Pin signature usage guide
- :doc:`chipflow-commands` - CLI command reference
- `RTL Debugger <https://github.com/amaranth-lang/rtl-debugger>`_ - Interactive debugging
- `CXXRTL Documentation <https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/write_cxxrtl.html>`_
