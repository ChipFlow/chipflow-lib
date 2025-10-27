Platform API Reference
======================

This page documents the complete public API of the ``chipflow_lib.platform`` module.

All symbols listed here are re-exported from submodules for convenience and can be imported directly from ``chipflow_lib.platform``.

Platforms
---------

.. autoclass:: chipflow_lib.platform.sim.SimPlatform
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.silicon.SiliconPlatform
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.silicon.SiliconPlatformPort
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.software.SoftwarePlatform
   :members:
   :undoc-members:
   :show-inheritance:

Build Steps
-----------

.. autoclass:: chipflow_lib.platform.base.StepBase
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.sim_step.SimStep
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.silicon_step.SiliconStep
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.software_step.SoftwareStep
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.board_step.BoardStep
   :members:
   :undoc-members:
   :show-inheritance:

IO Signatures
-------------

Base IO Signatures
~~~~~~~~~~~~~~~~~~

.. autoclass:: chipflow_lib.platform.io.iosignature.IOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.iosignature.OutputIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.iosignature.InputIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.iosignature.BidirIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

Protocol-Specific Signatures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: chipflow_lib.platform.io.signatures.UARTSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.signatures.GPIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.signatures.SPISignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.signatures.I2CSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.signatures.QSPIFlashSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.signatures.JTAGSignature
   :members:
   :undoc-members:
   :show-inheritance:

Software Integration
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: chipflow_lib.platform.io.signatures.SoftwareDriverSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.signatures.SoftwareBuild
   :members:
   :undoc-members:
   :show-inheritance:

.. autofunction:: chipflow_lib.platform.io.signatures.attach_data

IO Configuration
----------------

.. autoclass:: chipflow_lib.platform.io.iosignature.IOModel
   :members:
   :undoc-members:

.. autoclass:: chipflow_lib.platform.io.iosignature.IOModelOptions
   :members:
   :undoc-members:

.. autoclass:: chipflow_lib.platform.io.iosignature.IOTripPoint
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow_lib.platform.io.sky130.Sky130DriveMode
   :members:
   :undoc-members:
   :show-inheritance:

Utility Functions
-----------------

.. autofunction:: chipflow_lib.platform.base.setup_amaranth_tools

.. autofunction:: chipflow_lib.utils.top_components

.. autofunction:: chipflow_lib.utils.get_software_builds

Constants
---------

.. autodata:: chipflow_lib.platform.io.iosignature.IO_ANNOTATION_SCHEMA
   :annotation:
