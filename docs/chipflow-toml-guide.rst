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

``[chipflow.steps]``
--------------------

The ``steps`` section allows overriding or addition to the standard steps available from `chipflow_lib`_.

For example, if you want to override the standard silicon preparation step, you could derive from :class:`chipflow_lib.steps.silicon.SiliconStep`, add your custom functionality
and add the following to your `chipflow.toml`, with the appropriate Python `qualified name`_ :

.. code-block:: TOML

   [chipflow.stepe]
   silicon = "my_design.steps.silicon:SiliconStep"


You probably won't need to change these if you're starting from an example repository.

.. _chipflow_lib: https://github.com/ChipFlow/chipflow-lib]
.. _qualified name: https://docs.python.org/3/glossary.html#term-qualified-name


``[chipflow.clocks]``
---------------------

``[chipflow.silicon]``
----------------------

.. code-block:: TOML

   [chipflow.silicon]
   process = "ihp_sg13g2"
   package = "pga144"


The ``silicon`` section sets the Foundry ``process`` (i.e. PDK) that we are targeting for manufacturing, and the physical ``package`` we want to place our design inside.
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

Available pad rings
-------------------

+----------+-----------+--------------------+------------------------------------+
| Pad ring | Pad count | Pad locations      | Notes                              |
+==========+===========+====================+====================================+
+----------+-----------+--------------------+------------------------------------+
|| cf20    || 20       || ``N1`` ... ``N7`` ||   Bare die package with 20 pins   |
||         ||          || ``S1`` ... ``S7`` ||                                   |
||         ||          || ``E1`` ... ``E3`` ||                                   |
||         ||          || ``W1`` ... ``W3`` ||                                   |
+----------+-----------+--------------------+------------------------------------+
| pga144   | 144       | ``1`` ... ``144``  |                                    |
+----------+-----------+--------------------+------------------------------------+
|| TBA     ||          ||                   || If you require a different        |
||         ||          ||                   || pad ring, then please contact     |
||         ||          ||                   || customer support.                 |
+----------+-----------+--------------------+------------------------------------+




silicon.pads
============

The ``silicon.pads`` section lists special pads. In general you are unlikely to need to add to this. 

For each pad, there's a label which is used by our design, and what ``type`` and ``loc`` each pad should be.

type
----

The ``type`` for each pad can be set to one of:

clock
   External clock input.

i
   Input.

o
   Output.

io
   Input or output.

loc
----

This is the physical location of the pad on your chosen pad ring. How these are indexed varies by the pad ring.

silicon.power
=============

This section describes how the pads should be connected to the power available on the chosen process.

This is a work in progress, and currently you can use the defaults provided by customer support.


.. _Caravel Harness: https://caravel-harness.readthedocs.io/en/latest/
