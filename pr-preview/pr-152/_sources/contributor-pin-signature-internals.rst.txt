Pin Signature Architecture (Contributor Guide)
===============================================

This guide explains the internal architecture of ChipFlow's pin signature system, annotation infrastructure, and how platforms consume this metadata. This is intended for contributors who need to understand or extend the pin signature system.

Overview
--------

ChipFlow uses a sophisticated annotation system to attach metadata to Amaranth hardware designs. This metadata describes:

1. **I/O configuration** (drive modes, trip points, clock domains)
2. **Simulation models** (UIDs and parameters for testbench generation)
3. **Software drivers** (C/H files and register structures)
4. **Data attachments** (software binaries to load into flash)

This metadata is preserved through the entire flow from Python design → RTLIL → platform backends (silicon, simulation, software).

Annotation Infrastructure
--------------------------

Core Module: ``chipflow/platform/io/annotate.py``

The annotation system uses Amaranth's ``meta.Annotation`` framework combined with Pydantic for type-safe JSON schema generation.

amaranth_annotate() Decorator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The core function is ``amaranth_annotate()``:

.. code-block:: python

    def amaranth_annotate(
        modeltype: type[TypedDict],      # TypedDict defining the schema
        schema_id: str,                  # JSON schema $id (e.g., "https://chipflow.com/schemas/io-model/v0")
        member: str = '__chipflow_annotation__',  # Attribute name storing the data
        decorate_object: bool = False    # If True, decorates instances; if False, decorates classes
    ):

**How it works:**

1. Takes a ``TypedDict`` model and generates a JSON schema using Pydantic's ``TypeAdapter``
2. Creates an Amaranth ``meta.Annotation`` subclass with that schema
3. Returns a decorator that applies the annotation to classes or objects
4. The decorated class/object stores data in ``member`` attribute (e.g., ``self._model``)
5. When serializing to RTLIL, Amaranth calls ``Annotation.as_json()`` which extracts the data

**Example Usage:**

.. code-block:: python

    from typing_extensions import TypedDict, NotRequired
    from chipflow.platform.io.annotate import amaranth_annotate

    # Define schema as TypedDict
    class MyModel(TypedDict):
        name: str
        count: NotRequired[int]

    # Create decorator
    @amaranth_annotate(MyModel, "https://example.com/my-model/v1", "_my_data")
    class MySignature(wiring.Signature):
        def __init__(self, name: str, count: int = 1):
            # Store data in attribute that decorator will extract
            self._my_data = MyModel(name=name, count=count)
            super().__init__({"port": Out(wiring.Signature(...))})

**Key Points:**

- The decorator doesn't modify ``__init__`` - you must populate the data attribute yourself
- ``decorate_object=True`` is used with ``attach_data()`` to annotate signature instances
- Pydantic validates the data and provides JSON schema with proper types
- The schema is embedded in RTLIL annotations for downstream tools

submodule_metadata() Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Platforms extract annotations from the design using ``submodule_metadata()``:

.. code-block:: python

    def submodule_metadata(fragment: Fragment, top_name: str):
        """
        Generator that walks the Fragment tree and yields:
            (component, submodule_name, metadata_dict)

        metadata_dict contains:
            'annotations': dict mapping schema_id → annotation data
            'path': list of component names from root
        """

**Usage in Platforms:**

.. code-block:: python

    from chipflow.platform.io.annotate import submodule_metadata

    frag = Fragment.get(m, None)
    for component, name, meta in submodule_metadata(frag, "top"):
        annotations = meta['annotations']
        if DRIVER_MODEL_SCHEMA in annotations:
            driver_model = TypeAdapter(DriverModel).validate_python(
                annotations[DRIVER_MODEL_SCHEMA]
            )
            # Use driver_model data...

I/O Signature Base Classes
---------------------------

Core Module: ``chipflow/platform/io/iosignature.py``

IOModelOptions TypedDict
~~~~~~~~~~~~~~~~~~~~~~~~~

Defines all options for configuring I/O pins:

.. code-block:: python

    class IOModelOptions(TypedDict):
        invert: NotRequired[bool | Tuple[bool, ...]]
        individual_oe: NotRequired[bool]
        power_domain: NotRequired[str]
        clock_domain: NotRequired[str]
        buffer_in: NotRequired[bool]
        buffer_out: NotRequired[bool]
        sky130_drive_mode: NotRequired[Sky130DriveMode]
        trip_point: NotRequired[IOTripPoint]
        init: NotRequired[int | bool]
        init_oe: NotRequired[int | bool]

All fields use ``NotRequired`` to make them optional with sensible defaults.

IOModel TypedDict
~~~~~~~~~~~~~~~~~

Extends ``IOModelOptions`` with direction and width information:

.. code-block:: python

    class IOModel(IOModelOptions):
        direction: IODirection  # "input", "output", or "bidir"
        width: int

This is the complete model that gets annotated on I/O signatures.

IOSignature Base Class
~~~~~~~~~~~~~~~~~~~~~~~

The base class for all I/O signatures, decorated with ``@amaranth_annotate``:

.. code-block:: python

    @amaranth_annotate(IOModel, IO_ANNOTATION_SCHEMA, '_model')
    class IOSignature(wiring.Signature):
        def __init__(self, width: int, direction: IODirection, **kwargs: Unpack[IOModelOptions]):
            # Build the model from parameters
            model = IOModel(direction=direction, width=width, **kwargs)

            # Create appropriate signal structure based on direction
            if direction == "input":
                members = {"i": In(width)}
            elif direction == "output":
                members = {
                    "o": Out(width),
                    "oe": Out(1) if not individual_oe else Out(width)
                }
            elif direction == "bidir":
                members = {
                    "i": In(width),
                    "o": Out(width),
                    "oe": Out(1) if not individual_oe else Out(width)
                }

            # Store model for annotation extraction
            self._model = model

            super().__init__(members)

**Direction-Specific Subclasses:**

.. code-block:: python

    class InputIOSignature(IOSignature):
        def __init__(self, width: int, **kwargs):
            super().__init__(width, "input", **kwargs)

    class OutputIOSignature(IOSignature):
        def __init__(self, width: int, **kwargs):
            super().__init__(width, "output", **kwargs)

    class BidirIOSignature(IOSignature):
        def __init__(self, width: int, **kwargs):
            super().__init__(width, "bidir", **kwargs)

Concrete Pin Signatures
------------------------

Core Module: ``chipflow/platform/io/signatures.py``

Concrete pin signatures (UART, GPIO, SPI, etc.) combine I/O signatures with simulation metadata.

These signatures are annotations of the **type** of the external interface (UART, GPIO, SPI), allowing ChipFlow to select and typecheck suitable simulation models that match that interface type. The annotations are independent of any particular IP implementation - they describe the interface protocol, not the internal logic of peripherals.

simulatable_interface() Decorator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This decorator adds simulation model metadata for interface type identification:

.. code-block:: python

    def simulatable_interface(base="com.chipflow.chipflow"):
        def decorate(klass):
            # Apply amaranth_annotate for SimInterface
            dec = amaranth_annotate(SimInterface, SIM_ANNOTATION_SCHEMA)
            klass = dec(klass)

            # Wrap __init__ to populate __chipflow_annotation__
            original_init = klass.__init__
            def new_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                self.__chipflow_annotation__ = {
                    "uid": klass.__chipflow_uid__,
                    "parameters": self.__chipflow_parameters__(),
                }

            klass.__init__ = new_init
            klass.__chipflow_uid__ = f"{base}.{klass.__name__}"
            if not hasattr(klass, '__chipflow_parameters__'):
                klass.__chipflow_parameters__ = lambda self: []

            return klass
        return decorate

**What it does:**

1. Applies ``amaranth_annotate(SimInterface, ...)`` to the class
2. Assigns a unique identifier (UID) like ``"com.chipflow.chipflow.UARTSignature"``
3. Wraps ``__init__`` to populate ``__chipflow_annotation__`` with UID and parameters
4. Allows signatures to specify parameters via ``__chipflow_parameters__()`` method

Example: UARTSignature
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @simulatable_interface()
    class UARTSignature(wiring.Signature):
        def __init__(self, **kwargs: Unpack[IOModelOptions]):
            super().__init__({
                "tx": Out(OutputIOSignature(1, **kwargs)),
                "rx": Out(InputIOSignature(1, **kwargs)),
            })

**Annotations on this signature:**

1. ``SIM_ANNOTATION_SCHEMA``: ``{"uid": "com.chipflow.chipflow.UARTSignature", "parameters": []}``
2. Nested ``IO_ANNOTATION_SCHEMA`` on ``tx`` and ``rx`` sub-signatures

Example: GPIOSignature with Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @simulatable_interface()
    class GPIOSignature(wiring.Signature):
        def __init__(self, pin_count=1, **kwargs: Unpack[IOModelOptions]):
            self._pin_count = pin_count
            self._options = kwargs
            kwargs['individual_oe'] = True  # Force individual OE for GPIO
            super().__init__({
                "gpio": Out(BidirIOSignature(pin_count, **kwargs))
            })

        def __chipflow_parameters__(self):
            # Expose pin_count as a parameter for simulation models
            return [('pin_count', self._pin_count)]

**Annotations:**

1. ``SIM_ANNOTATION_SCHEMA``: ``{"uid": "...", "parameters": [["pin_count", 8]]}``
2. Nested ``IO_ANNOTATION_SCHEMA`` on ``gpio`` with ``width=8, individual_oe=True``

SoftwareDriverSignature
~~~~~~~~~~~~~~~~~~~~~~~~

This signature wrapper attaches driver files to peripherals:

.. code-block:: python

    class SoftwareDriverSignature(wiring.Signature):
        def __init__(self, members, **kwargs: Unpack[DriverModel]):
            # Extract base path from component's module file
            definition_file = sys.modules[kwargs['component'].__module__].__file__
            base_path = Path(definition_file).parent.absolute()
            kwargs['_base_path'] = base_path

            # Default to 'bus' if not specified
            if 'regs_bus' not in kwargs:
                kwargs['regs_bus'] = 'bus'

            # Convert generators to lists
            for k in ('c_files', 'h_files', 'include_dirs'):
                if k in kwargs:
                    kwargs[k] = list(kwargs[k])

            # Store and annotate
            self.__chipflow_driver_model__ = kwargs
            amaranth_annotate(DriverModel, DRIVER_MODEL_SCHEMA,
                            '__chipflow_driver_model__', decorate_object=True)(self)

            super().__init__(members=members)

**DriverModel TypedDict:**

.. code-block:: python

    class DriverModel(TypedDict):
        component: wiring.Component | dict  # Component metadata
        regs_struct: str                   # C struct name (e.g., "uart_regs_t")
        h_files: NotRequired[list[Path]]   # Header files
        c_files: NotRequired[list[Path]]   # C source files
        include_dirs: NotRequired[list[Path]]  # Include directories
        regs_bus: NotRequired[str]         # Bus member name (default: "bus")
        _base_path: NotRequired[Path]      # Auto-filled: peripheral's directory

**Example Usage in a Peripheral:**

.. code-block:: python

    from chipflow.platforms import UARTSignature, SoftwareDriverSignature
    from amaranth_soc import csr

    class UARTPeripheral(wiring.Component):
        def __init__(self, *, addr_width=5, data_width=8):
            super().__init__(
                SoftwareDriverSignature(
                    members={
                        "bus": In(csr.Signature(addr_width=addr_width, data_width=data_width)),
                        "pins": Out(UARTSignature()),
                    },
                    component=self,
                    regs_struct='uart_regs_t',
                    c_files=['drivers/uart.c'],
                    h_files=['drivers/uart.h']
                )
            )

attach_data() Function
~~~~~~~~~~~~~~~~~~~~~~~

Attaches data (like ``SoftwareBuild``) to both external and internal flash interfaces:

.. code-block:: python

    def attach_data(external_interface: wiring.PureInterface,
                   component: wiring.Component,
                   data: DataclassProtocol):
        # Create Data annotation with the dataclass
        data_dict: Data = {'data': data}

        # Annotate both the component's signature and external interface
        for sig in (component.signature, external_interface.signature):
            setattr(sig, '__chipflow_data__', data_dict)
            amaranth_annotate(Data, DATA_SCHEMA, '__chipflow_data__',
                            decorate_object=True)(sig)

**Why annotate both?**

- External interface is visible at top-level for simulation testbench
- Internal component holds the implementation for software platform
- Both need access to the binary data for their respective purposes

Platform Consumption
--------------------

Silicon Platform
~~~~~~~~~~~~~~~~

Core Module: ``chipflow/platform/silicon.py``

The silicon platform creates actual I/O ports from pin signatures.

**SiliconPlatformPort Class:**

.. code-block:: python

    class SiliconPlatformPort(io.PortLike, Generic[Pin]):
        def __init__(self, name: str, port_desc: PortDesc):
            self.name = name
            self.port_desc = port_desc

            # Extract IOModel from port_desc
            iomodel = port_desc.iomodel
            direction = iomodel.direction
            width = iomodel.width
            invert = iomodel.get('invert', False)
            init = iomodel.get('init', 0)
            init_oe = iomodel.get('init_oe', 0)
            individual_oe = iomodel.get('individual_oe', False)

            # Create signals based on direction
            if direction in ("input", "bidir"):
                self.i = Signal(width, name=f"{name}__i")
            if direction in ("output", "bidir"):
                self.o = Signal(width, init=init, name=f"{name}__o")
                if individual_oe:
                    self.oe = Signal(width, init=init_oe, name=f"{name}__oe")
                else:
                    self.oe = Signal(1, init=init_oe, name=f"{name}__oe")

            # Store invert for wire_up
            self._invert = invert

**Port Creation from Pinlock:**

The platform reads the top-level signature and creates ports:

.. code-block:: python

    # chipflow/platform/silicon.py (in SiliconPlatform.create_ports)
    for key in top.signature.members.keys():
        member = getattr(top, key)
        port_desc = self._get_port_desc(member)  # Extracts IOModel from annotations
        port = Sky130Port(key, port_desc)
        self._ports[key] = port

**Sky130Port - Process-Specific Extension:**

.. code-block:: python

    class Sky130Port(SiliconPlatformPort):
        _DriveMode_map = {
            Sky130DriveMode.STRONG_UP_WEAK_DOWN: 0b011,
            Sky130DriveMode.OPEN_DRAIN_STRONG_UP: 0b101,
            # ...
        }

        _VTrip_map = {
            IOTripPoint.CMOS: (0, 0),
            IOTripPoint.TTL: (0, 1),
            # ...
        }

        def __init__(self, name: str, port_desc: PortDesc):
            super().__init__(name, port_desc)

            # Extract Sky130-specific options
            iomodel = port_desc.iomodel
            drive_mode = iomodel.get('sky130_drive_mode', Sky130DriveMode.STRONG_UP_WEAK_DOWN)
            trip_point = iomodel.get('trip_point', IOTripPoint.CMOS)

            # Create configuration signals for Sky130 I/O cell
            self.dm = Const(self._DriveMode_map[drive_mode], 3)
            self.ib_mode_sel, self.vtrip_sel = self._VTrip_map[trip_point]
            # ... more Sky130-specific configuration

Software Platform
~~~~~~~~~~~~~~~~~

Core Module: ``chipflow/platform/software.py``

The software platform extracts driver models and builds software.

**SoftwarePlatform.build():**

.. code-block:: python

    class SoftwarePlatform:
        def build(self, m, top):
            frag = Fragment.get(m, None)
            driver_models = {}
            roms = {}

            # Extract annotations from all top-level members
            for key in top.keys():
                for component, name, meta in submodule_metadata(frag, key):
                    annotations = meta['annotations']

                    # Extract driver models
                    if DRIVER_MODEL_SCHEMA in annotations:
                        driver_models[name] = TypeAdapter(DriverModel).validate_python(
                            annotations[DRIVER_MODEL_SCHEMA]
                        )

                    # Extract software builds
                    if DATA_SCHEMA in annotations:
                        data = annotations[DATA_SCHEMA]
                        if data['data']['type'] == "SoftwareBuild":
                            roms[name] = TypeAdapter(SoftwareBuild).validate_python(
                                data['data']
                            )

            # Find wishbone decoder to get memory map
            wb_decoder = # ... find decoder
            windows = get_windows(wb_decoder)

            # Create software generator
            sw = SoftwareGenerator(...)

            # Add each peripheral with its driver
            for component, driver_model in driver_models.items():
                addr = windows[component][0][0]
                sw.add_periph(component, addr, driver_model)

            return {key: sw}

**SoftwareGenerator - Code Generation:**

Located in ``chipflow/software/soft_gen.py``:

.. code-block:: python

    class SoftwareGenerator:
        def add_periph(self, name, address, model: DriverModel):
            # Resolve driver file paths relative to peripheral's directory
            base_path = model['_base_path']
            for k in ('c_files', 'h_files', 'include_dirs'):
                if k in model:
                    for p in model[k]:
                        if not p.is_absolute():
                            self._drivers[k].add(base_path / p)
                        else:
                            self._drivers[k].add(p)

            # Store peripheral info for soc.h generation
            component = model['component']['name']
            regs_struct = model['regs_struct']
            self._periphs.add(Periph(name, component, regs_struct, address))

        def generate(self):
            # Generate soc.h with peripheral #defines
            # Generate start.S with startup code
            # Generate sections.lds with memory layout
            pass

**Generated soc.h Example:**

.. code-block:: c

    #ifndef SOC_H
    #define SOC_H

    #include "drivers/uart.h"
    #include "drivers/gpio.h"

    #define UART_0 ((volatile uart_regs_t *const)0x02000000)
    #define GPIO_0 ((volatile gpio_regs_t *const)0x01000000)

    #define putc(x) uart_putc(UART_0, x)
    #define puts(x) uart_puts(UART_0, x)

    #endif

Complete Flow Example
---------------------

Let's trace a complete example from signature definition to platform usage.

Step 1: Define a Peripheral with Driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # chipflow_digital_ip/io/_uart.py
    from chipflow.platforms import UARTSignature, SoftwareDriverSignature

    class UARTPeripheral(wiring.Component):
        def __init__(self, *, init_divisor=0):
            super().__init__(
                SoftwareDriverSignature(
                    members={
                        "bus": In(csr.Signature(addr_width=5, data_width=8)),
                        "pins": Out(UARTSignature()),  # <-- External interface
                    },
                    component=self,
                    regs_struct='uart_regs_t',
                    c_files=['drivers/uart.c'],
                    h_files=['drivers/uart.h']
                )
            )
            # ... implementation

Step 2: Use in Top-Level Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # design/design.py
    class MySoC(wiring.Component):
        def __init__(self):
            super().__init__({
                "uart": Out(UARTSignature()),  # <-- Top-level interface
            })

        def elaborate(self, platform):
            m = Module()

            # Instantiate peripheral
            m.submodules.uart = uart = UARTPeripheral(init_divisor=217)

            # Connect to top-level
            connect(m, flipped(self.uart), uart.pins)

            return m

Step 3: Annotations Applied
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**On ``self.uart`` (top-level):**

- ``SIM_ANNOTATION_SCHEMA``: ``{"uid": "com.chipflow.chipflow.UARTSignature", "parameters": []}``
- ``IO_ANNOTATION_SCHEMA`` on ``tx``: ``{"direction": "output", "width": 1, ...}``
- ``IO_ANNOTATION_SCHEMA`` on ``rx``: ``{"direction": "input", "width": 1, ...}``

**On ``uart.signature`` (peripheral):**

- ``DRIVER_MODEL_SCHEMA``:

  .. code-block:: json

      {
        "component": {"name": "UARTPeripheral", "file": "/path/to/_uart.py"},
        "regs_struct": "uart_regs_t",
        "c_files": ["drivers/uart.c"],
        "h_files": ["drivers/uart.h"],
        "regs_bus": "bus",
        "_base_path": "/path/to/chipflow_digital_ip/io"
      }

- Same simulation and I/O annotations on nested ``pins`` member

Step 4: Silicon Platform Consumption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # During silicon elaboration
    silicon_platform = SiliconPlatform(config)

    # Creates Sky130Port for "uart"
    port = Sky130Port("uart", port_desc_from_annotations)

    # port.tx.o, port.tx.oe created as signals
    # port.rx.i created as signal
    # Configuration based on IOModel (drive modes, trip points)

Step 5: Software Platform Consumption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # During software build
    software_platform = SoftwarePlatform(config)
    generators = software_platform.build(m, top)

    # Extracts DriverModel from uart.signature annotations
    # Adds peripheral to SoftwareGenerator:
    #   name="uart", addr=0x02000000, driver_model={...}

    # Generates soc.h:
    #   #include "drivers/uart.h"
    #   #define UART ((volatile uart_regs_t *const)0x02000000)

Step 6: User Software Uses Generated API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    // user_code.c
    #include "soc.h"

    void main() {
        uart_init(UART, 217);  // Uses generated UART pointer
        uart_puts(UART, "Hello from ChipFlow!\n");
    }

Adding New Pin Signatures
--------------------------

To add a new pin signature type:

1. **Define the signature class:**

   .. code-block:: python

       @simulatable_interface()
       class MyNewSignature(wiring.Signature):
           def __init__(self, param1, param2, **kwargs: Unpack[IOModelOptions]):
               self._param1 = param1
               self._param2 = param2
               super().__init__({
                   "signal1": Out(OutputIOSignature(width1, **kwargs)),
                   "signal2": Out(InputIOSignature(width2, **kwargs)),
               })

           def __chipflow_parameters__(self):
               return [('param1', self._param1), ('param2', self._param2)]

2. **Add to exports in** ``chipflow/platform/__init__.py``
3. **Add to re-export in** ``chipflow/platforms/__init__.py`` (for backward compatibility)
4. **Create simulation model** (if needed) matching the UID
5. **Update documentation** in ``docs/using-pin-signatures.rst``

Adding Custom Platform Backends
--------------------------------

To add a new platform that consumes annotations:

1. **Import annotation infrastructure:**

   .. code-block:: python

       from chipflow.platform.io.annotate import submodule_metadata
       from chipflow.platform.io.signatures import DRIVER_MODEL_SCHEMA, SIM_ANNOTATION_SCHEMA
       from pydantic import TypeAdapter

2. **Walk the design and extract annotations:**

   .. code-block:: python

       frag = Fragment.get(m, None)
       for component, name, meta in submodule_metadata(frag, "top"):
           annotations = meta['annotations']

           # Check for your schema
           if MY_SCHEMA_ID in annotations:
               my_data = TypeAdapter(MyModel).validate_python(annotations[MY_SCHEMA_ID])
               # Process my_data...

3. **Use the extracted data** for your platform-specific operations

JSON Schema Integration
-----------------------

All annotations generate JSON schemas that are:

- Embedded in RTLIL ``(* chipflow.annotation.{schema_id} *)`` attributes
- Validated using JSON Schema Draft 2020-12
- Accessible to external tools via RTLIL parsing

**Schema URI Convention:**

.. code-block:: python

    from chipflow.platform.io.iosignature import _chipflow_schema_uri

    # Generates: "https://chipflow.com/schemas/my-thing/v0"
    MY_SCHEMA = str(_chipflow_schema_uri("my-thing", 0))

**Pydantic Integration:**

Pydantic's ``TypeAdapter`` provides:

- Automatic JSON schema generation from ``TypedDict``
- Runtime validation when deserializing
- Type hints for IDE support
- Serialization to JSON-compatible Python dicts

Key Files
---------

- ``chipflow/platform/io/annotate.py`` - Core annotation infrastructure
- ``chipflow/platform/io/iosignature.py`` - I/O signature base classes
- ``chipflow/platform/io/signatures.py`` - Concrete signatures and decorators
- ``chipflow/platform/silicon.py`` - Silicon platform consumption
- ``chipflow/platform/software.py`` - Software platform consumption
- ``chipflow/software/soft_gen.py`` - Code generation

See Also
--------

- :doc:`using-pin-signatures` - User-facing guide for using pin signatures
