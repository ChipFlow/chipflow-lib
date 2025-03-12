chipflow_lib.platforms.silicon
==============================

.. py:module:: chipflow_lib.platforms.silicon


Classes
-------

.. autoapisummary::

   chipflow_lib.platforms.silicon.SiliconPlatformPort
   chipflow_lib.platforms.silicon.SiliconPlatform


Module Contents
---------------

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


