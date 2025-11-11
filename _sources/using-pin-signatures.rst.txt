Using Pin Signatures and Software Drivers
==========================================

This guide explains how to use ChipFlow's pin signature system and attach software drivers to your hardware designs.

Overview
--------

ChipFlow provides a standardized way to:

1. Define external pin interfaces for your design using **Pin Signatures** (UARTSignature, GPIOSignature, etc.)
2. Attach software driver code to peripherals using **SoftwareDriverSignature**
3. Connect pre-built software binaries to flash memory using **attach_data()**

Pin Signatures
--------------

Pin signatures define the external interface of your design. ChipFlow provides several built-in signatures for common peripherals:

Available Pin Signatures
~~~~~~~~~~~~~~~~~~~~~~~~

- ``UARTSignature()`` - Serial UART interface (TX, RX)
- ``GPIOSignature(pin_count)`` - General purpose I/O pins
- ``SPISignature()`` - SPI master interface (SCK, COPI, CIPO, CSN)
- ``I2CSignature()`` - I2C bus interface (SCL, SDA)
- ``QSPIFlashSignature()`` - Quad SPI flash interface
- ``JTAGSignature()`` - JTAG debug interface

All pin signatures accept ``IOModelOptions`` to customize their electrical and behavioral properties (see below).

Using Pin Signatures in Your Top-Level Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pin signatures are used when defining your top-level component's interface:

.. testcode::

    # Define a simple SoC with external interfaces
    class MySoC(wiring.Component):
        def __init__(self):
            super().__init__({
                "uart": Out(UARTSignature()),
                "gpio": Out(GPIOSignature(pin_count=8)),
                "flash": Out(QSPIFlashSignature()),
            })

    # Verify the component can be instantiated
    soc = MySoC()
    assert hasattr(soc, 'uart')
    assert hasattr(soc, 'gpio')
    assert hasattr(soc, 'flash')

These signatures tell ChipFlow:

- How to connect your design to the physical pins of your chip
- How to select appropriate simulation models for each external interface type
- How to simulate signals and test the interface in a virtual environment
- Requirements for pad and package pin allocation (power domains, drive strength, etc.)

Pin signatures are generic and independent of any particular IP implementation, allowing ChipFlow to match the interface type (UART, GPIO, SPI) to appropriate simulation models and test infrastructure.

IO Model Options
~~~~~~~~~~~~~~~~

All pin signatures accept ``IOModelOptions`` to configure the electrical and behavioral properties of the I/O pins:

.. code-block:: python

    from chipflow.platforms import GPIOSignature, IOTripPoint

    super().__init__({
        # Basic GPIO
        "gpio_basic": Out(GPIOSignature(pin_count=4)),

        # GPIO with custom options
        "gpio_custom": Out(GPIOSignature(
            pin_count=8,
            invert=True,              # Invert all pins
            individual_oe=True,       # Separate OE for each pin
            clock_domain='io_clk',    # Use IO clock domain
            trip_point=IOTripPoint.TTL,  # TTL input thresholds
            init=0x00,                # Initial output values
            init_oe=0xFF              # Initial OE values (all enabled)
        ))
    })

Available IOModelOptions
^^^^^^^^^^^^^^^^^^^^^^^^

- **invert** (``bool`` or ``Tuple[bool, ...]``) - Polarity inversion for pins. Can be a single bool for all pins or a tuple specifying inversion per pin.
- **individual_oe** (``bool``) - If ``True``, each output wire has its own Output Enable bit. If ``False`` (default), a single OE bit controls the entire port.
- **power_domain** (``str``) - Name of the I/O power domain. Pins with different power domains must be in separate signatures.
- **clock_domain** (``str``) - Name of the I/O's clock domain (default: ``'sync'``). Pins with different clock domains must be in separate signatures.
- **buffer_in** (``bool``) - Enable input buffer on the I/O pad.
- **buffer_out** (``bool``) - Enable output buffer on the I/O pad.
- **sky130_drive_mode** (:class:`Sky130DriveMode`) - Drive mode for Sky130 output buffers (see below).
- **trip_point** (:class:`IOTripPoint`) - Input buffer trip point configuration:

  - ``IOTripPoint.CMOS`` - CMOS switching levels (30%/70%) referenced to I/O power domain
  - ``IOTripPoint.TTL`` - TTL levels (low < 0.8V, high > 2.0V)
  - ``IOTripPoint.VCORE`` - CMOS levels referenced to core power domain
  - ``IOTripPoint.VREF`` - CMOS levels referenced to external reference voltage
  - ``IOTripPoint.SCHMITT_TRIGGER`` - Schmitt trigger for noise immunity

- **init** (``int`` or ``bool``) - Initial values for output signals.
- **init_oe** (``int`` or ``bool``) - Initial values for output enable signals.

Sky130-Specific Pin Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Sky130 chips, you can configure the I/O cell drive mode:

.. code-block:: python

    from chipflow.platforms import Sky130DriveMode, GPIOSignature

    # Use open-drain with strong pull-down for I2C
    super().__init__({
        "i2c_gpio": Out(GPIOSignature(
            pin_count=2,
            sky130_drive_mode=Sky130DriveMode.OPEN_DRAIN_STRONG_DOWN
        ))
    })

Software Driver Signatures
---------------------------

The ``SoftwareDriverSignature`` allows you to attach C/C++ driver code to your hardware peripherals. This is useful for providing software APIs that match your hardware registers.

Creating a Peripheral with Driver Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's how to create a peripheral that includes software driver code:

.. code-block:: python

    from amaranth.lib.wiring import In, Out
    from amaranth_soc import csr
    from chipflow.platforms import UARTSignature, SoftwareDriverSignature

    class UARTPeripheral(wiring.Component):
        def __init__(self, *, addr_width=5, data_width=8, init_divisor=0):
            # Your peripheral implementation here...

            # Define the signature with driver code attached
            super().__init__(
                SoftwareDriverSignature(
                    members={
                        "bus": In(csr.Signature(addr_width=addr_width, data_width=data_width)),
                        "pins": Out(UARTSignature()),
                    },
                    component=self,
                    regs_struct='uart_regs_t',      # Name of register struct in C
                    c_files=['drivers/uart.c'],     # C implementation files
                    h_files=['drivers/uart.h']      # Header files
                )
            )

Driver File Organization
~~~~~~~~~~~~~~~~~~~~~~~~

Driver files should be placed relative to your peripheral's Python file:

.. code-block:: text

    chipflow_digital_ip/io/
    ├── _uart.py                  # Peripheral definition
    └── drivers/
        ├── uart.h                # Header with register struct and API
        └── uart.c                # Implementation

Example Header File (uart.h)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    #ifndef UART_H
    #define UART_H

    #include <stdint.h>

    // Register structure matching your hardware
    typedef struct __attribute__((packed, aligned(4))) {
        uint8_t config;
        uint8_t padding_0[3];
        uint32_t phy_config;
        uint8_t status;
        uint8_t data;
        uint8_t padding_1[6];
    } uart_mod_regs_t;

    typedef struct __attribute__((packed, aligned(4))) {
        uart_mod_regs_t rx;
        uart_mod_regs_t tx;
    } uart_regs_t;

    // Driver API
    void uart_init(volatile uart_regs_t *uart, uint32_t divisor);
    void uart_putc(volatile uart_regs_t *uart, char c);
    void uart_puts(volatile uart_regs_t *uart, const char *s);

    #endif

The register structure must use ``__attribute__((packed, aligned(4)))`` to match the hardware layout.

Example Implementation File (uart.c)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    #include "uart.h"

    void uart_init(volatile uart_regs_t *uart, uint32_t divisor) {
        uart->tx.config = 0;
        uart->tx.phy_config = divisor & 0x00FFFFFF;
        uart->tx.config = 1;
        uart->rx.config = 0;
        uart->rx.phy_config = divisor & 0x00FFFFFF;
        uart->rx.config = 1;
    }

    void uart_putc(volatile uart_regs_t *uart, char c) {
        if (c == '\n')
            uart_putc(uart, '\r');
        while (!(uart->tx.status & 0x1))
            ;
        uart->tx.data = c;
    }

Using Peripherals in Your SoC
------------------------------

Here's a complete example of using peripherals with driver code in your top-level design:

.. code-block:: python

    from amaranth import Module
    from amaranth.lib.wiring import Out, flipped, connect
    from amaranth_soc import csr

    from chipflow_digital_ip.io import UARTPeripheral, GPIOPeripheral
    from chipflow.platforms import UARTSignature, GPIOSignature

    class MySoC(wiring.Component):
        def __init__(self):
            super().__init__({
                "uart_0": Out(UARTSignature()),
                "gpio_0": Out(GPIOSignature(pin_count=8)),
            })

        def elaborate(self, platform):
            m = Module()

            # Create CSR decoder for peripheral access
            csr_decoder = csr.Decoder(addr_width=28, data_width=8)
            m.submodules.csr_decoder = csr_decoder

            # Instantiate UART peripheral
            m.submodules.uart_0 = uart_0 = UARTPeripheral(
                init_divisor=int(25e6//115200)
            )
            csr_decoder.add(uart_0.bus, name="uart_0", addr=0x02000000)

            # Connect to top-level pins
            connect(m, flipped(self.uart_0), uart_0.pins)

            # Instantiate GPIO peripheral
            m.submodules.gpio_0 = gpio_0 = GPIOPeripheral(pin_count=8)
            csr_decoder.add(gpio_0.bus, name="gpio_0", addr=0x01000000)

            # Connect to top-level pins
            connect(m, flipped(self.gpio_0), gpio_0.pins)

            return m

The driver code is automatically collected during the ChipFlow build process and made available to your software.

Attaching Software Binaries
----------------------------

The ``attach_data()`` function allows you to attach pre-built software binaries (like bootloaders) to flash memory interfaces.

Basic Usage
~~~~~~~~~~~

.. code-block:: python

    from pathlib import Path
    from chipflow.platforms import attach_data, SoftwareBuild

    def elaborate(self, platform):
        m = Module()

        # ... create your flash peripheral (spiflash) ...

        # Build software from source files
        sw = SoftwareBuild(
            sources=Path('design/software').glob('*.c'),
            offset=0x100000  # Start at 1MB offset in flash
        )

        # Attach to both internal and external interfaces
        attach_data(self.flash, m.submodules.spiflash, sw)

        return m

The ``attach_data()`` function:

1. Takes the **external interface** (``self.flash``) from your top-level component
2. Takes the **internal component** (``m.submodules.spiflash``) that implements the flash controller
3. Takes the **SoftwareBuild** object describing the software to build and load

The software is automatically compiled, linked, and loaded into the simulation or silicon design.

SoftwareBuild Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    SoftwareBuild(
        sources,           # List or glob of .c source files
        includes=[],       # List of .h include files to copy
        include_dirs=[],   # Additional include directories
        offset=0           # Offset in flash memory (in bytes)
    )

Complete Example
----------------

Here's a complete working example combining all concepts:

.. code-block:: python

    from pathlib import Path
    from amaranth import Module
    from amaranth.lib import wiring
    from amaranth.lib.wiring import Out, flipped, connect
    from amaranth_soc import csr, wishbone

    from chipflow_digital_ip.io import UARTPeripheral, GPIOPeripheral
    from chipflow_digital_ip.memory import QSPIFlash
    from chipflow.platforms import (
        UARTSignature, GPIOSignature, QSPIFlashSignature,
        Sky130DriveMode, attach_data, SoftwareBuild
    )

    class MySoC(wiring.Component):
        def __init__(self):
            # Define top-level pin interfaces
            super().__init__({
                "flash": Out(QSPIFlashSignature()),
                "uart": Out(UARTSignature()),
                "gpio": Out(GPIOSignature(pin_count=8)),
                "i2c_pins": Out(GPIOSignature(
                    pin_count=2,
                    sky130_drive_mode=Sky130DriveMode.OPEN_DRAIN_STRONG_UP
                ))
            })

            self.csr_base = 0xb0000000
            self.bios_offset = 0x100000  # 1MB

        def elaborate(self, platform):
            m = Module()

            # Create bus infrastructure
            csr_decoder = csr.Decoder(addr_width=28, data_width=8)
            m.submodules.csr_decoder = csr_decoder

            # QSPI Flash with driver
            m.submodules.flash = flash = QSPIFlash(addr_width=24, data_width=32)
            csr_decoder.add(flash.csr_bus, name="flash", addr=0x00000000)
            connect(m, flipped(self.flash), flash.pins)

            # UART with driver (115200 baud at 25MHz clock)
            m.submodules.uart = uart = UARTPeripheral(
                init_divisor=int(25e6//115200)
            )
            csr_decoder.add(uart.bus, name="uart", addr=0x02000000)
            connect(m, flipped(self.uart), uart.pins)

            # GPIO with driver
            m.submodules.gpio = gpio = GPIOPeripheral(pin_count=8)
            csr_decoder.add(gpio.bus, name="gpio", addr=0x01000000)
            connect(m, flipped(self.gpio), gpio.pins)

            # I2C pins (using GPIO with open-drain)
            m.submodules.i2c = i2c_gpio = GPIOPeripheral(pin_count=2)
            csr_decoder.add(i2c_gpio.bus, name="i2c", addr=0x01100000)
            connect(m, flipped(self.i2c_pins), i2c_gpio.pins)

            # Build and attach BIOS software
            sw = SoftwareBuild(
                sources=Path('design/software').glob('*.c'),
                offset=self.bios_offset
            )
            attach_data(self.flash, flash, sw)

            return m

**Note:** For more advanced examples including CPU cores and Wishbone bus integration, see the `chipflow-examples repository <https://github.com/ChipFlow/chipflow-examples>`_, which contains tested and working SoC designs.

See Also
--------

- :doc:`chipflow-toml-guide` - Configuring your ChipFlow project
- :doc:`platform-api` - Complete platform API including SimPlatform and attach_data
- `ChipFlow Examples <https://github.com/ChipFlow/chipflow-examples>`_ - Complete working examples with CPU and Wishbone bus
