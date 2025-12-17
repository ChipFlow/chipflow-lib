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
   from chipflow.config.parser import _parse_config_file
   _parse_config_file("docs/example-chipflow.toml")

``[chipflow]`` table
--------------------

|required|

The top level configuration for inputs to the ChipFlow tools.


project_name
============

|required|

The ``project_name`` is a human-readable identifier for this project. If not set, the tool and library will use the project name configured in ``pyproject.toml``.

.. code-block:: TOML

   [chipflow]
   project_name = 'my_project'

clock_domains
=============

|optional|

A list of top-level clock domains for your design. If omitted, defaults to the `Amaranth` default ``sync``, and sync is always assumed to be the name of the core clock for bringup.

.. code-block:: TOML

   [chipflow]
   clock_domains = ['sync', 'peripheral']


``[chipflow.top]`` table
------------------------

|required|

This section outlines the design modules that need to be instantiated.
A new top module will be automatically generated, incorporating all specified modules along with their interfaces.
Each entry follows the format `<instance name> = <module class path>`.

The instance name is the name the python object will be given in your design, and the :term:`module class path`

.. code-block:: TOML

   [chipflow.top]
   soc = "my_design.design:MySoC"

.. glossary::

   module class path
       The module class path offers a way to locate Python objects as entry points.
       It consists of a module's :term:`qualified name` followed by a colon (:) and then the :term:`qualified name` of the class within that module.

.. _chipflow-toml-steps:

``[chipflow.steps]`` table
--------------------------

|optional|

The ``steps`` section allows overriding or addition to the standard steps available from `chipflow`.

For example, if you want to override the standard silicon preparation step, you could derive from :class:`chipflow.steps.silicon.SiliconStep`, add your custom functionality
and add the following to your `chipflow.toml`, with the appropriate :term:`module class path`:

.. code-block:: TOML

   [chipflow.steps]
   silicon = "my_design.steps.silicon:SiliconStep"


You probably won't need to change these if you're starting from an example repository.

.. _chipflow: https://github.com/ChipFlow/chipflow-lib


``[chipflow.silicon]``
----------------------

|required|

The ``silicon`` section sets the Foundry ``process`` (i.e. PDK) that we are targeting for manufacturing, and the physical ``package`` (including pad ring) we want to place our design inside.

You'll choose the ``process`` and ``package`` based in the requirements of your design.


.. code-block:: TOML

   [chipflow.silicon]
   process = "ihp_sg13g2"
   package = "pga144"


process
=======

|required|

Foundry process to use

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


package
=======

|required|

The form of IC packaging to use

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
