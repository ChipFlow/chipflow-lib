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


``[chipflow.clocks]``
---------------------

.. code-block:: TOML

   [chipflow.clocks]
   default = 'sys_clk'

This section links the clock domains utilized in the design to specific pads.
These pads need to be specified in the `[silicon.pads]`_ section with the :term:type set to :term:clock.
The ``default`` clock domain is associated with the Amaranth :any:`sync <lang-domains>` :ref:`clock domain <lang-clockdomains>`.
Currently, only one ``default`` clock domain is supported.


``[chipflow.resets]``
---------------------

.. code-block:: TOML

   [chipflow.resets]
   default = 'sys_rst_n'

This section identifies the input pads designated for reset functionality.
These pads need to be specified in the `[silicon.pads]`_ section with the :term:type set to :term:reset.
The logic that synchronizes the reset signal with the clock will be generated automatically.

``[chipflow.silicon]``
----------------------

.. code-block:: TOML

   [chipflow.silicon]
   process = "ihp_sg13g2"
   package = "pga144"


The ``silicon`` section sets the Foundry ``process`` (i.e. PDK) that we are targeting for manufacturing, and the physical ``package`` (pad ring) we want to place our design inside.
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
| pga144   | 144       | ``1`` ... ``144``  |                                    |
+----------+-----------+--------------------+------------------------------------+
|| TBA     ||          ||                   || If you require a different        |
||         ||          ||                   || pad ring, then please contact     |
||         ||          ||                   || customer support.                 |
+----------+-----------+--------------------+------------------------------------+


``[silicon.pads]``
------------------

The ``silicon.pads`` section lists special pads. In general you are unlikely to need to add to this.
Each pad specified with the name used by the design and two parameters: :term:type and :term:`loc`.

.. code-block:: TOML

   [chipflow.silicon.pads]
   sys_clk   = { type = "clock", loc = "114" }
   sys_rst_n = { type = "reset", loc = "115" }

In the above example two pads specified, ``sys_clk`` pad for clock input and ``sys_rst_n`` for reset.

.. glossary::

   loc
       This is the physical location of the pad on your chosen pad ring. How these are indexed varies by the pad ring.

   type
       The :term:type for each pad can be set to one of :term:clock or :term:reset.

   clock
       External clock input.

   reset
       External reset input.


``[silicon.power]``
-------------------

This section outlines the connection of pads to the power supply available for the selected process and package.
These pads are declared with the :term:type and :term:loc parameters, similar to the `[silicon.pads]`_ section.
Note that in this context, the :term:type parameter can only be ``ground`` or ``power``.

This is a work in progress, and currently you can use the defaults provided by customer support.

.. _Caravel Harness: https://caravel-harness.readthedocs.io/en/latest/
