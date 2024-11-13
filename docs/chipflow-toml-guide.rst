Intro to chipflow.toml
======================

The ``chipflow.toml`` file provides configuration for your design with the ChipFlow platform.

Let's start with a typical example:

.. literalinclude:: example-chipflow.toml
   :language: toml

.. testcode::
   :hide:

   # Assert that example-chipflow.toml matches the current config schema. If 
   # this test fails, then its likely that the content in this file will need
   # to be updated.
   from chipflow_lib.cli import _parse_config_file
   _parse_config_file("docs/example-chipflow.toml")

project_id
===========

The ``project_id`` is set to the project ID which you can get from the ChipFlow app project page.

steps
=====

The ``steps`` define the Python class which will be used as an entry point to these parts of the ChipFlow process.
You probably won't need to change these if you're starting from an example repository.

silicon
=======

The ``silicon`` section sets the Foundry ``process`` we are targeting for manufacturing, and the physical ``pad_ring`` we want to place our design inside.
You'll choose the ``process`` and ``pad_ring`` based in the requirements of your design. 

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
|| caravel || TBC      || TBC               || The `Caravel Harness`_ contains   |
||         ||          ||                   || additional logic which wraps your |
||         ||          ||                   || design.                           |
||         ||          ||                   || It handles its own power pins.    |
+----------+-----------+--------------------+------------------------------------+
|| cf20    || 20       || ``N1`` ... ``N7`` ||                                   |
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

The ``silicon.pads`` section lists the pads we will be using. 

For each pad, there's a label which is used by our design, and what ``type`` and ``loc`` each pad should be.

type
----

The ``type`` for each pad can be set to one of:

clk
   External clock.

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
