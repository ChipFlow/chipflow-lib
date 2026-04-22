Platform API Reference
======================

This page provides the API reference for the ``chipflow.platform`` module.

All symbols listed here are re-exported from submodules for convenience and can be imported directly from ``chipflow.platform``.

.. toctree::
   :maxdepth: 3

   /chipflow-lib/autoapi/chipflow/index

Quick Links
-----------

**Platforms:**

- :py:class:`chipflow.platform.SimPlatform` - Simulation platform
- :py:class:`chipflow.platform.SiliconPlatform` - Silicon/ASIC platform
- :py:class:`chipflow.platform.SoftwarePlatform` - Software build platform

**Build Steps:**

- :py:class:`chipflow.platform.StepBase` - Base class for build steps
- :py:class:`chipflow.platform.SimStep` - Simulation step
- :py:class:`chipflow.platform.SiliconStep` - Silicon build step
- :py:class:`chipflow.platform.SoftwareStep` - Software build step
- :py:class:`chipflow.platform.BoardStep` - Board programming step

**IO Signatures:**

- :py:class:`chipflow.platform.IOSignature` - Base IO signature class
- :py:class:`chipflow.platform.OutputIOSignature` - Output-only signature
- :py:class:`chipflow.platform.InputIOSignature` - Input-only signature
- :py:class:`chipflow.platform.BidirIOSignature` - Bidirectional signature
- :py:class:`chipflow.platform.UARTSignature` - UART interface signature
- :py:class:`chipflow.platform.GPIOSignature` - GPIO interface signature
- :py:class:`chipflow.platform.SPISignature` - SPI interface signature
- :py:class:`chipflow.platform.I2CSignature` - I2C interface signature
- :py:class:`chipflow.platform.QSPIFlashSignature` - QSPI Flash signature
- :py:class:`chipflow.platform.JTAGSignature` - JTAG interface signature

**Software Integration:**

- :py:class:`chipflow.platform.SoftwareDriverSignature` - Signature with driver code
- :py:class:`chipflow.platform.SoftwareBuild` - Software build configuration
- :py:func:`chipflow.platform.attach_data` - Attach software to flash memory

**IO Configuration:**

- :py:class:`chipflow.platform.IOModel` - IO model data
- :py:class:`chipflow.platform.IOModelOptions` - IO model options
- :py:class:`chipflow.platform.IOTripPoint` - Input buffer trip point
- :py:class:`chipflow.platform.Sky130DriveMode` - Sky130 drive mode configuration
