Platform API Reference
======================

This page documents the complete public API of the ``chipflow.platform`` module.

All symbols listed here are re-exported from submodules for convenience and can be imported directly from ``chipflow.platform``.

Platforms
---------

.. autoclass:: chipflow.platform.sim.SimPlatform
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.silicon.SiliconPlatform
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.silicon.SiliconPlatformPort
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.software.SoftwarePlatform
   :members:
   :undoc-members:
   :show-inheritance:

Build Steps
-----------

.. autoclass:: chipflow.platform.base.StepBase
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.sim_step.SimStep
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.silicon_step.SiliconStep
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.software_step.SoftwareStep
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.board_step.BoardStep
   :members:
   :undoc-members:
   :show-inheritance:

IO Signatures
-------------

Base IO Signatures
~~~~~~~~~~~~~~~~~~

.. autoclass:: chipflow.platform.io.iosignature.IOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.iosignature.OutputIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.iosignature.InputIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.iosignature.BidirIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

Protocol-Specific Signatures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: chipflow.platform.io.signatures.UARTSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.signatures.GPIOSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.signatures.SPISignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.signatures.I2CSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.signatures.QSPIFlashSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.signatures.JTAGSignature
   :members:
   :undoc-members:
   :show-inheritance:

Software Integration
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: chipflow.platform.io.signatures.SoftwareDriverSignature
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.signatures.SoftwareBuild
   :members:
   :undoc-members:
   :show-inheritance:

.. autofunction:: chipflow.platform.io.signatures.attach_data

IO Configuration
----------------

.. autoclass:: chipflow.platform.io.iosignature.IOModel
   :members:
   :undoc-members:

.. autoclass:: chipflow.platform.io.iosignature.IOModelOptions
   :members:
   :undoc-members:

.. autoclass:: chipflow.platform.io.iosignature.IOTripPoint
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: chipflow.platform.io.sky130.Sky130DriveMode
   :members:
   :undoc-members:
   :show-inheritance:

Utility Functions
-----------------

.. autofunction:: chipflow.platform.base.setup_amaranth_tools

.. autofunction:: chipflow.utils.top_components

.. autofunction:: chipflow.utils.get_software_builds

Constants
---------

.. autodata:: chipflow.platform.io.iosignature.IO_ANNOTATION_SCHEMA
   :annotation:
