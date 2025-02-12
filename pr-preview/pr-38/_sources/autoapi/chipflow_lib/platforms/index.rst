chipflow_lib.platforms
======================

.. py:module:: chipflow_lib.platforms


Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/chipflow_lib/platforms/silicon/index
   /autoapi/chipflow_lib/platforms/sim/index
   /autoapi/chipflow_lib/platforms/utils/index


Attributes
----------

.. autoapisummary::

   chipflow_lib.platforms.PIN_ANNOTATION_SCHEMA
   chipflow_lib.platforms.PACKAGE_DEFINITIONS


Classes
-------

.. autoapisummary::

   chipflow_lib.platforms.SiliconPlatformPort
   chipflow_lib.platforms.SiliconPlatform
   chipflow_lib.platforms.SimPlatform
   chipflow_lib.platforms.PinSignature


Functions
---------

.. autoapisummary::

   chipflow_lib.platforms.OutputPinSignature
   chipflow_lib.platforms.InputPinSignature
   chipflow_lib.platforms.BidirPinSignature
   chipflow_lib.platforms.load_pinlock
   chipflow_lib.platforms.top_interfaces


Package Contents
----------------

.. py:class:: SiliconPlatformPort(component, name, port, *, invert = False)

   Bases: :py:obj:`amaranth.lib.io.PortLike`


   Represents an abstract library I/O port that can be passed to a buffer.

   The port types supported by most platforms are :class:`SingleEndedPort` and
   :class:`DifferentialPort`. Platforms may define additional port types where appropriate.

   .. note::

       :class:`amaranth.hdl.IOPort` is not an instance of :class:`amaranth.lib.io.PortLike`.


   .. py:property:: i


   .. py:property:: o


   .. py:property:: oe


   .. py:property:: direction

      Direction of the port.

      :rtype: :class:`Direction`


   .. py:property:: pins


   .. py:property:: invert


.. py:class:: SiliconPlatform(config)

   .. py:method:: instantiate_ports(m)


   .. py:method:: request(name=None, **kwargs)


   .. py:method:: get_io_buffer(buffer)


   .. py:method:: add_file(filename, content)


   .. py:method:: build(elaboratable, name='top')


   .. py:method:: default_clock(platform, clock, reset)


.. py:class:: SimPlatform

   .. py:attribute:: build_dir


   .. py:attribute:: extra_files


   .. py:attribute:: clk


   .. py:attribute:: rst


   .. py:attribute:: buttons


   .. py:attribute:: sim_boxes


   .. py:method:: add_file(filename, content)


   .. py:method:: add_model(inst_type, iface, edge_det=[])


   .. py:method:: add_monitor(inst_type, iface)


   .. py:method:: build(e)


.. py:data:: PIN_ANNOTATION_SCHEMA
   :value: ''


.. py:class:: PinSignature(direction, width=1, init=None)

   Bases: :py:obj:`amaranth.lib.wiring.Signature`


   Amaranth Signtaure used to decorate wires that would
   usually be brought out onto a pin on the package.


   .. py:method:: annotations(*args)

      Annotate an interface object.

      Subclasses of :class:`Signature` may override this method to provide annotations for
      a corresponding interface object. The default implementation provides none.

      See :mod:`amaranth.lib.meta` for details.

      :returns: :py:`tuple()`
      :rtype: iterable of :class:`~.meta.Annotation`



.. py:function:: OutputPinSignature(width, **kwargs)

.. py:function:: InputPinSignature(width, **kwargs)

.. py:function:: BidirPinSignature(width, **kwargs)

.. py:function:: load_pinlock()

.. py:data:: PACKAGE_DEFINITIONS

.. py:function:: top_interfaces(config)

