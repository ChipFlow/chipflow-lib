chipflow_lib.steps.silicon
==========================

.. py:module:: chipflow_lib.steps.silicon


Attributes
----------

.. autoapisummary::

   chipflow_lib.steps.silicon.logger


Classes
-------

.. autoapisummary::

   chipflow_lib.steps.silicon.SiliconTop
   chipflow_lib.steps.silicon.SiliconStep


Module Contents
---------------

.. py:data:: logger

.. py:class:: SiliconTop(config={})

   Bases: :py:obj:`amaranth.Elaboratable`


   .. py:method:: elaborate(platform)


.. py:class:: SiliconStep(config)

   Prepare and submit the design for an ASIC.


   .. py:attribute:: config


   .. py:attribute:: project_name


   .. py:attribute:: silicon_config


   .. py:attribute:: platform


   .. py:method:: build_cli_parser(parser)


   .. py:method:: run_cli(args)


   .. py:method:: prepare()

      Elaborate the design and convert it to RTLIL.

      Returns the path to the RTLIL file.



   .. py:method:: submit(rtlil_path, *, dry_run=False)

      Submit the design to the ChipFlow cloud builder.




