ChipFlow Architecture Overview
==============================

This guide explains the overall architecture of ChipFlow and how different components work together to transform your Python hardware design into manufacturable silicon.

High-Level Overview
-------------------

ChipFlow follows a multi-stage flow from Python design to silicon:

.. code-block:: text

    ┌─────────────────┐
    │  Python Design  │  Your Amaranth HDL design with ChipFlow signatures
    │  (design.py)    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   Elaboration   │  Amaranth converts to Fragment tree
    │                 │  ChipFlow annotations attached
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │     RTLIL       │  Intermediate representation with annotations
    │  (design.rtlil) │  JSON schemas embedded as attributes
    └────────┬────────┘
             │
             ├─────────────┬────────────────┬──────────────┐
             │             │                │              │
             ▼             ▼                ▼              ▼
    ┌────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
    │  Silicon   │  │  Simulation  │  │ Software │  │  Board   │
    │  Platform  │  │   Platform   │  │ Platform │  │ Platform │
    └────────────┘  └──────────────┘  └──────────┘  └──────────┘
         │                │                 │             │
         ▼                ▼                 ▼             ▼
     GDS-II          CXXRTL C++        soc.h + .elf    Bitstream

Core Components
---------------

ChipFlow consists of several key subsystems that work together:

1. **Pin Signatures** - Define external interfaces (UART, GPIO, SPI, etc.)
2. **Annotation System** - Attach metadata to designs for platform consumption
3. **Package Definitions** - Map abstract ports to physical pins
4. **Platforms** - Transform RTLIL to target-specific outputs
5. **Steps** - Orchestrate the build process via CLI commands
6. **Configuration** - TOML-based project configuration

Design Flow in Detail
---------------------

1. User Defines Design
~~~~~~~~~~~~~~~~~~~~~~

You write your design in Python using Amaranth HDL and ChipFlow signatures:

.. testcode::

    class MySoC(wiring.Component):
        def __init__(self):
            super().__init__({
                "uart": Out(UARTSignature()),
                "gpio": Out(GPIOSignature(pin_count=8)),
            })

        def elaborate(self, platform):
            m = Module()
            # Your design logic here
            return m

    # Verify the design can be instantiated
    design = MySoC()
    assert hasattr(design, 'uart')
    assert hasattr(design, 'gpio')

2. Signatures Add Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~

ChipFlow signatures are decorated with ``@amaranth_annotate`` which adds JSON schema metadata:

- **IOModel**: I/O configuration for external interfaces of the IC (direction, width, drive modes, trip points)
- **SimInterface**: Interface type identification for matching simulation models (UID, parameters)
- **DriverModel**: Software drivers for the IP block (C/H files, register structures)
- **Data**: Software binaries to load into memory (flash images, bootloaders)

This metadata is preserved through the entire flow.

3. Pin Allocation
~~~~~~~~~~~~~~~~~

When you run ``chipflow pin lock``:

.. code-block:: text

    Top-level Interface
    (MySoC.uart, MySoC.gpio)
           │
           ▼
    Extract IOSignatures
    (UARTSignature, GPIOSignature)
           │
           ▼
    Calculate Pin Requirements
    (UART: 2 pins, GPIO: 8 pins)
           │
           ▼
    Package Allocator
    (Selects pins from package definition)
           │
           ▼
    pins.lock File
    (Persists allocation)

The ``pins.lock`` file maps abstract interface names to concrete package pin locations:

.. code-block:: javascript

    {
      "uart.tx": {"pin": "42", "loc": "A12"},
      "uart.rx": {"pin": "43", "loc": "A13"},
      "gpio.gpio[0]": {"pin": "44", "loc": "B12"},
      ...
    }

4. Elaboration & RTLIL Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Amaranth elaborates your design into a ``Fragment`` tree, then converts to RTLIL:

.. code-block:: text

    Fragment Tree                RTLIL
    ┌──────────┐                ┌────────────────────────┐
    │   Top    │                │ module \MySoC          │
    │          │                │   (* chipflow.io = ... │
    ├──────────┤   ────────>    │   wire \uart$tx$o      │
    │ MySoC    │                │   ...                  │
    │  - uart  │                │ endmodule              │
    │  - gpio  │                │                        │
    └──────────┘                └────────────────────────┘

Annotations from signatures are embedded in RTLIL as attributes:

.. code-block:: verilog

    (* chipflow.annotation.io-model = "{\"direction\": \"output\", \"width\": 1}" *)
    wire \uart$tx$o;

5. Platform Consumption
~~~~~~~~~~~~~~~~~~~~~~~

Different platforms consume the RTLIL + annotations:

Silicon Platform
^^^^^^^^^^^^^^^^

.. code-block:: text

    RTLIL + pins.lock
          │
          ▼
    Read IOModel annotations
    (drive mode, trip point, etc.)
          │
          ▼
    Create SiliconPlatformPort
    (Sky130Port, etc.)
          │
          ▼
    Generate I/O cell configuration
    (PAD instances with controls)
          │
          ▼
    Synthesis → Place & Route → GDS-II

Simulation Platform
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    RTLIL
      │
      ▼
    Read SimInterface annotations
    (UID, parameters)
      │
      ▼
    Match to C++ models
    (UART model, SPI flash model)
      │
      ▼
    Generate CXXRTL C++
      │
      ▼
    Compile with models → Executable simulator

Software Platform
^^^^^^^^^^^^^^^^^

.. code-block:: text

    Design Fragment
          │
          ▼
    Read DriverModel annotations
    (C/H files, regs_struct)
          │
          ▼
    Extract memory map from Wishbone decoder
          │
          ▼
    Generate soc.h with peripheral pointers
          │
          ▼
    Compile user code + drivers → ELF binary

6. Step Orchestration
~~~~~~~~~~~~~~~~~~~~~~

The ``chipflow`` CLI uses "Steps" to orchestrate the flow:

.. code-block:: text

    $ chipflow silicon prepare
           │
           ▼
    ┌─────────────┐
    │ SiliconStep │
    │  .prepare() │
    └─────────────┘
           │
           ├─> Load config (chipflow.toml)
           ├─> Instantiate top components
           ├─> Load pins.lock
           ├─> Create SiliconPlatform
           ├─> Elaborate design
           └─> Convert to RTLIL → build/silicon/design.rtlil

    $ chipflow silicon submit
           │
           ▼
    ┌─────────────┐
    │ SiliconStep │
    │  .submit()  │
    └─────────────┘
           │
           ├─> Package RTLIL + pins.lock
           ├─> Authenticate with API
           └─> Upload to ChipFlow cloud

Annotation System Architecture
-------------------------------

The annotation system is central to how ChipFlow propagates metadata:

1. **Decorator Application** (Design time)

   .. code-block:: python

       @amaranth_annotate(IOModel, "https://chipflow.com/schemas/io-model/v0", "_model")
       class IOSignature(wiring.Signature):
           def __init__(self, width, direction, **kwargs):
               self._model = IOModel(width=width, direction=direction, **kwargs)
               # Decorator will extract self._model when serializing

2. **JSON Schema Generation** (Elaboration time)

   Pydantic TypeAdapter generates JSON schema from TypedDict:

   .. code-block:: javascript

       {
         "$schema": "https://json-schema.org/draft/2020-12/schema",
         "$id": "https://chipflow.com/schemas/io-model/v0",
         "type": "object",
         "properties": {
           "direction": {"type": "string", "enum": ["input", "output", "bidir"]},
           "width": {"type": "integer"},
           "invert": {"type": "boolean"},
           ...
         }
       }

3. **RTLIL Embedding** (Conversion time)

   Amaranth calls ``Annotation.as_json()`` and embeds in RTLIL:

   .. code-block:: verilog

       (* chipflow.annotation.io-model = "{\"direction\": \"output\", \"width\": 1}" *)

4. **Platform Extraction** (Build time)

   Platform uses ``submodule_metadata()`` to walk Fragment and extract:

   .. code-block:: python

       for component, name, meta in submodule_metadata(frag, "top"):
           annotations = meta['annotations']
           if IO_ANNOTATION_SCHEMA in annotations:
               io_model = TypeAdapter(IOModel).validate_python(annotations[IO_ANNOTATION_SCHEMA])
               # Use io_model to configure platform

Package System Architecture
----------------------------

Packages define the physical constraints of your chip:

.. code-block:: text

    BasePackageDef
         ├── bringup_pins() → PowerPins, JTAGPins, etc.
         ├── allocate() → Assigns ports to pins
         └── instantiate() → Creates PortDesc for each allocation

    LinearAllocPackageDef (extends BasePackageDef)
         └── Sequential allocation strategy

    QuadPackageDef (extends LinearAllocPackageDef)
         └── PGA-style packages (pga144)

    GAPackageDef (extends BasePackageDef)
         └── Grid array packages with row/col addressing

    OpenframePackageDef (extends BasePackageDef)
         └── Open-frame packages with custom layouts

Allocation Flow:

.. code-block:: text

    User runs: chipflow pin lock
           │
           ▼
    ┌──────────────────────┐
    │ Load chipflow.toml   │
    │ - process: sky130    │
    │ - package: pga144    │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Instantiate package  │
    │ PACKAGE_DEFS[pkg]    │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Elaborate top design │
    │ Extract interfaces   │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ For each interface:  │
    │ - Get IOModel        │
    │ - Create PortDesc    │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ package.allocate()   │
    │ - Assign pins        │
    │ - Check constraints  │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Write pins.lock      │
    │ - Persist mapping    │
    └──────────────────────┘

Configuration System
--------------------

ChipFlow uses Pydantic models for configuration:

.. code-block:: text

    chipflow.toml
         │ (parsed by tomllib)
         ▼
    dict[str, Any]
         │ (validated by Pydantic)
         ▼
    Config dataclass
    ├── chipflow: ChipFlowConfig
    │   ├── project_name: str
    │   ├── top: dict[str, str]
    │   ├── clock_domains: list[str]
    │   ├── silicon: SiliconConfig
    │   │   ├── process: Process
    │   │   └── package: str
    │   ├── software: SoftwareConfig
    │   │   └── riscv: CompilerConfig
    │   └── simulation: SimulationConfig
    └── tool: dict[str, Any]

Steps access config during execution:

.. code-block:: python

    class SiliconStep(StepBase):
        def prepare(self):
            process = self.config.chipflow.silicon.process
            package = PACKAGE_DEFS[self.config.chipflow.silicon.package]
            # Use process and package to build...

Extending ChipFlow
------------------

ChipFlow is designed to be extensible at multiple levels:

Custom Pin Signatures
~~~~~~~~~~~~~~~~~~~~~

Create new interface types:

.. code-block:: python

    @simulatable_interface()
    class MyCustomSignature(wiring.Signature):
        def __init__(self, **kwargs):
            super().__init__({
                "custom": Out(BidirIOSignature(4, **kwargs))
            })

To attach a simulation model to your custom signature:

.. code-block:: python

    from chipflow_lib.platform import SimModel, BasicCxxBuilder

    # Define the C++ model
    MY_BUILDER = BasicCxxBuilder(
        models=[
            SimModel('my_custom', 'my_namespace', MyCustomSignature),
        ],
        hpp_files=[Path('design/sim/my_custom_model.h')],
    )

    # In your custom SimStep
    class MySimPlatform(SimPlatform):
        def __init__(self, config):
            super().__init__(config)
            self._builders.append(MY_BUILDER)

See :doc:`simulation-guide` for complete examples of creating custom simulation models.

Custom Steps
~~~~~~~~~~~~

Override default behavior:

.. code-block:: python

    from chipflow_lib.platform import SiliconStep

    class MySiliconStep(SiliconStep):
        def prepare(self):
            # Custom pre-processing
            result = super().prepare()
            # Custom post-processing
            return result

Reference in ``chipflow.toml``:

.. code-block:: toml

    [chipflow.steps]
    silicon = "my_project.steps:MySiliconStep"

Custom Packages
~~~~~~~~~~~~~~~

Define new package types:

.. code-block:: python

    from chipflow_lib.packaging import BasePackageDef

    class MyPackageDef(BasePackageDef):
        def __init__(self):
            # Define pin layout
            pass

        def allocate(self, ports):
            # Custom allocation algorithm
            pass

Custom Platforms
~~~~~~~~~~~~~~~~

Add new target platforms:

.. code-block:: python

    from chipflow_lib.platform import StepBase

    class MyPlatformStep(StepBase):
        def build(self, m, top):
            # Extract annotations
            # Generate output for custom platform
            pass

See Also
--------

- :doc:`using-pin-signatures` - User guide for pin signatures
- :doc:`contributor-pin-signature-internals` - Deep dive into annotation system
- :doc:`chipflow-toml-guide` - Configuration reference
- :doc:`chipflow-commands` - CLI command reference
