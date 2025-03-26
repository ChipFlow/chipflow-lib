chipflow_lib.pin_lock
=====================

.. py:module:: chipflow_lib.pin_lock


Attributes
----------

.. autoapisummary::

   chipflow_lib.pin_lock.logger


Classes
-------

.. autoapisummary::

   chipflow_lib.pin_lock.PinCommand


Functions
---------

.. autoapisummary::

   chipflow_lib.pin_lock.count_member_pins
   chipflow_lib.pin_lock.allocate_pins
   chipflow_lib.pin_lock.lock_pins


Module Contents
---------------

.. py:data:: logger

.. py:function:: count_member_pins(name, member)

   Counts the pins from amaranth metadata


.. py:function:: allocate_pins(name, member, pins, port_name = None)

   Allocate pins based of Amaranth member metadata


.. py:function:: lock_pins()

.. py:class:: PinCommand(config)

   .. py:attribute:: config


   .. py:method:: build_cli_parser(parser)


   .. py:method:: run_cli(args)


   .. py:method:: lock()

      Lock the pin map for the design.

      Will attempt to reuse previous pin positions.



