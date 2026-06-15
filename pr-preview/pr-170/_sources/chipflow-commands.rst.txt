The ``chipflow`` command
==========================

The ``chipflow`` tool enables you to simulate your design or submit it to the ChipFlow cloud build service.
It implements several subcommands, which can be customised or added to in the ``steps`` section of :ref:`chipflow.toml<chipflow-toml-steps>`.

.. _chipflow_toml: chipflow-toml-guide.rst

``chipflow auth``
-----------------

The ``chipflow auth`` command manages authentication with the ChipFlow API.

``chipflow auth login``
~~~~~~~~~~~~~~~~~~~~~~~

Authenticate with the ChipFlow API using one of the following methods (tried in order):

1. **GitHub CLI token** (recommended) - If you have ``gh`` installed and authenticated, this method is instant
2. **Device flow** - Opens your browser to authorize via GitHub OAuth

Your API key will be saved locally in ``~/.config/chipflow/credentials`` for future use.

Options:

- ``--force``: Force re-authentication even if already logged in

Examples::

   # Authenticate (will auto-detect best method)
   chipflow auth login

   # Force re-authentication
   chipflow auth login --force

``chipflow auth logout``
~~~~~~~~~~~~~~~~~~~~~~~~

Remove saved credentials from your system::

   chipflow auth logout

``chipflow pin lock``
---------------------

The ``chipflow pin lock`` command performs pin locking for the current design.
For every new top level interface with containing external pins with a ``IOSignature`` that is discovered, the necessary number of package pins is allocated and the mapping saved in the ``pins.lock`` file.
This means that, unless the ``pins.lock`` file is deleted or manually modified, the pin assignments of all existing pins will always remain the same.

``chipflow silicon``
--------------------

The ``chipflow silicon`` subcommand is used to send the design to the cloud builder for build and tapeout. In general, it would be run inside GitHub Actions as part of a CI job.

 - ``chipflow silicon prepare`` links the design, including all Amaranth modules and any external Verilog components, into a single RTLIL file that is ready to be sent to the cloud builder.
 - ``chipflow silicon submit`` sends the linked design along with the ``pins.lock`` file containing pinout information to the ChipFlow cloud service for the build. With the ``--dry-run`` argument, it can be used for a local test that the design is ready to be submitted.

Authentication for submission:

1. If you've run ``chipflow auth login``, your saved credentials will be used automatically
2. If ``CHIPFLOW_API_KEY`` environment variable is set, it will be used
3. Otherwise, if ``gh`` (GitHub CLI) is installed and authenticated, it will authenticate automatically
4. As a last resort, you'll be prompted to complete device flow authentication

Most users should simply run ``chipflow auth login`` once and authentication will be automatic for all future submissions.

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
