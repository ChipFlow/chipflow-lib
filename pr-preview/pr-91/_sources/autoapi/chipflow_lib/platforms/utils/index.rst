chipflow_lib.platforms.utils
============================

.. py:module:: chipflow_lib.platforms.utils


Attributes
----------

.. autoapisummary::

   chipflow_lib.platforms.utils.PIN_ANNOTATION_SCHEMA
   chipflow_lib.platforms.utils.PACKAGE_DEFINITIONS


Classes
-------

.. autoapisummary::

   chipflow_lib.platforms.utils.IOSignature


Functions
---------

.. autoapisummary::

   chipflow_lib.platforms.utils.OutputIOSignature
   chipflow_lib.platforms.utils.InputIOSignature
   chipflow_lib.platforms.utils.BidirIOSignature
   chipflow_lib.platforms.utils.load_pinlock
   chipflow_lib.platforms.utils.top_interfaces


Module Contents
---------------

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

.. py:data:: PACKAGE_DEFINITIONS

.. py:function:: load_pinlock()

.. py:function:: top_interfaces(config)

