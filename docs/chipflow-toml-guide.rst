Intro to ``chipflow.toml``
==========================

The ``chipflow.toml`` file provides configuration for your design with the ChipFlow platform.

Let's start with a typical example:

.. literalinclude:: example-chipflow.toml
   :language: toml

.. testcode::
   :hide:

   # Assert that example-chipflow.toml matches the current config schema. If
   # this test fails, then its likely that the content in this file will need
   # to be updated.
   from chipflow_lib import _parse_config_file
   _parse_config_file("docs/example-chipflow.toml")

``[chipflow]``
--------------

.. code-block:: TOML

   [chipflow]
   project_name = "my_project"


The ``project_name`` is a human-readable identifier for this project. If not set, the tool and library will use the project name configured in ``pyproject.toml``.

``[chipflow.top]``
------------------

.. code-block:: TOML

   [chipflow.top]
   soc = "my_design.design:MySoC"

This section outlines the design modules that need to be instantiated.
A new top module will be automatically generated, incorporating all specified modules along with their interfaces.
Each entry follows the format `<instance name> = <module class path>`.

The instance name is the name the python object will be given in your design, and the :term:`module class path`

.. glossary::

   module class path
       The module class path offers a way to locate Python objects as entry points.
       It consists of a module's :term:`qualified name` followed by a colon (:) and then the :term:`qualified name` of the class within that module.

.. _chipflow-toml-steps:

``[chipflow.steps]``
--------------------

The ``steps`` section allows overriding or addition to the standard steps available from `chipflow_lib`.

For example, if you want to override the standard silicon preparation step, you could derive from :class:`chipflow_lib.steps.silicon.SiliconStep`, add your custom functionality
and add the following to your `chipflow.toml`, with the appropriate :term:`module class path`:

.. code-block:: TOML

   [chipflow.steps]
   silicon = "my_design.steps.silicon:SiliconStep"


You probably won't need to change these if you're starting from an example repository.

.. _chipflow_lib: https://github.com/ChipFlow/chipflow-lib


Clock Definitions
-----------------

The clock pins to be allocation on the package are determined from the top level clock domains exposed by components in `[chipflow.top]`.



``[chipflow.resets]``
---------------------

.. code-block:: TOML

   [chipflow.resets]
   default = 'sys_rst_n'

This section identifies the input pads designated for reset functionality.
These pads need to be specified in the `[silicon.pads]`_ section with the :term:`type` set to :term:`reset`.
The logic that synchronizes the reset signal with the clock will be generated automatically.

``[chipflow.silicon]``
----------------------

.. code-block:: TOML

   [chipflow.silicon]
   process = "ihp_sg13g2"
   package = "pga144"


The ``silicon`` section sets the Foundry ``process`` (i.e. PDK) that we are targeting for manufacturing, and the physical ``package`` (including pad ring) we want to place our design inside.

You'll choose the ``process`` and ``package`` based in the requirements of your design.

Available processes
-------------------

+------------+------------+---------------------------+
|| Process   || Supported || Notes                    |
||           || pad rings ||                          |
+============+============+===========================+
| sky130     | caravel    | Skywater 130nm            |
+------------+------------+---------------------------+
| gf180      | caravel    | GlobalFoundries 180nm     |
+------------+------------+---------------------------+
| gf130bcd   | pga144     | GlobalFoundries 130nm BCD |
+------------+------------+---------------------------+
| ihp_sg13g2 | pga144     | IHP SG13G2 130nm SiGe     |
+------------+------------+---------------------------+

Available Package Definitions
-----------------------------

+----------+-----------+--------------------+------------------------------------+
| Pad ring | Pad count | Pad locations      | Notes                              |
+==========+===========+====================+====================================+
+----------+-----------+--------------------+------------------------------------+
| pga144   | 144       | ``1`` ... ``144``  |                                    |
+----------+-----------+--------------------+------------------------------------+
|| TBA     ||          ||                   || If you require a different        |
||         ||          ||                   || pad ring, then please contact     |
||         ||          ||                   || customer support.                 |
+----------+-----------+--------------------+------------------------------------+



Power connections
-----------------

The package definition provides default locations for pins needed for bringup and test, like core power, ground, clock and reset, along with JTAG.

These can be determined by calling `BasePackageDef.bringup_pins`.

For ports that require their own power lines, you can set ``allocate_power`` and ``power_voltage`` in their `IOSignature`.

.. glossary::

   loc
       This is the physical location of the pad on your chosen pad ring. How these are indexed varies by the pad ring.

   type
       The :term:`type` for each pad can be set to one of :term:`clock` or :term:`reset`.

   clock
       External clock input.

   reset
       External reset input.


.. _Caravel Harness: https://caravel-harness.readthedocs.io/en/latest/
