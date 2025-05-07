The ``chipflow`` command
==========================

The ``chipflow`` tool enables you to simulate your design or submit it to the ChipFlow cloud build service.
It implements several subcommands, which can be customised or added to in the ``steps`` section of :ref:`chipflow.toml<chipflow-toml-steps>`.

.. _chipflow_toml: chipflow-toml-guide.rst

``chipflow pin lock``
---------------------

The ``chipflow pin lock`` command performs pin locking for the current design.
For every new top level interface with containing external pins with a ``PinSignature`` that is discovered, the necessary number of package pins is allocated and the mapping saved in the ``pins.lock`` file.
This means that, unless the ``pins.lock`` file is deleted or manually modified, the pin assignments of all existing pins will always remain the same.

``chipflow silicon``
--------------------

The ``chipflow silicon`` subcommand is used to send the design to the cloud builder for build and tapeout. In general, it would be run inside GitHub Actions as part of a CI job.

 - ``chipflow silicon prepare`` links the design, including all Amaranth modules and any external Verilog components, into a single RTLIL file that is ready to be sent to the cloud builder.
 - ``chipflow silicon submit`` sends the linked design along with the ``pins.lock`` file containing pinout information to the ChipFlow cloud service for the build. With the ``--dry-run`` argument, it can be used for a local test that the design is ready to be submitted.

Submitting the design to the cloud requires the ``CHIPFLOW_API_KEY`` environment variable to be set with a valid API key obtained from the cloud interface.

``chipflow sim``
----------------

The ``chipflow sim build`` command is used to build a CXXRTL simulation of the design; converting the design to a fast compiled C++ format along with C++ models of any peripherals.

Extra C++ model files for the simulation, and any custom build steps required, can be added to the ``sim/doit_build.py`` `doit <https://pydoit.org/>`_ build script inside the user project.

A default simulation driver (the C++ code that runs the simulation) is included as `main.cc <https://github.com/ChipFlow/chipflow-examples/blob/main/minimal/design/sim/main.cc>`_ in the example projects. This code:

 - Instantiates the user design; and the simulation models for the peripherals (SPI flash, UART and GPIO)
 - Initialises the CXXRTL debug agent, which is required to perform debugging with the `RTL Debugger <https://github.com/amaranth-lang/rtl-debugger>`_ VS Code extension
 - Configures input and output JSON files for stimuli and results respectively (for automated integration testing)
 - Runs the design for 3,000,000 clock cycles

``chipflow software``
---------------------

If the design contains a CPU, the ``chipflow software build`` command is used to build test firmware for the target CPU. Which C source files to include, and any build options (like the target architecture or enabled RISC-V extensions) can be customised in the ``software/doit_build.py`` doit build script inside the user project.
