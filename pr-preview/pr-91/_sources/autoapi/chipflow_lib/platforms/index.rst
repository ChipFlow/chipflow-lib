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
   chipflow_lib.platforms.IOSignature


Functions
---------

.. autoapisummary::

   chipflow_lib.platforms.OutputIOSignature
   chipflow_lib.platforms.InputIOSignature
   chipflow_lib.platforms.BidirIOSignature
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


   .. py:method:: wire(m, interface)


   .. py:property:: i


   .. py:property:: o


   .. py:property:: oe


   .. py:property:: direction

      Direction of the port.

      :rtype: :class:`Direction`


   .. py:property:: pins


   .. py:property:: invert


.. py:class:: SiliconPlatform(config)

   .. py:property:: ports


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


.. py:class:: IOSignature(direction, width = 1, all_have_oe = False, init=None)

   Bases: :py:obj:`amaranth.lib.wiring.Signature`


   Amaranth Signtaure used to decorate wires that would
   usually be brought out onto a port on the package.

   direction: Input, Output or Bidir
   width: width of port
   all_have_oe: For Bidir ports, should Output Enable be per wire or for the whole port
   init: a  :ref:`const-castable object <lang-constcasting>` for the initial values of the port


   .. py:property:: direction


   .. py:method:: width()


   .. py:method:: options()


   .. py:method:: annotations(*args)

      Annotate an interface object.

      Subclasses of :class:`Signature` may override this method to provide annotations for
      a corresponding interface object. The default implementation provides none.

      See :mod:`amaranth.lib.meta` for details.

      :returns: :py:`tuple()`
      :rtype: iterable of :class:`~.meta.Annotation`



.. py:function:: OutputIOSignature(width, **kwargs)

.. py:function:: InputIOSignature(width, **kwargs)

.. py:function:: BidirIOSignature(width, **kwargs)

.. py:function:: load_pinlock()

.. py:data:: PACKAGE_DEFINITIONS

.. py:function:: top_interfaces(config)

