chipflow_lib.software.soft_gen
==============================

.. py:module:: chipflow_lib.software.soft_gen


Classes
-------

.. autoapisummary::

   chipflow_lib.software.soft_gen.SoftwareGenerator


Module Contents
---------------

.. py:class:: SoftwareGenerator(*, rom_start, rom_size, ram_start, ram_size)

   .. py:attribute:: rom_start


   .. py:attribute:: rom_size


   .. py:attribute:: ram_start


   .. py:attribute:: ram_size


   .. py:attribute:: defines
      :value: []



   .. py:attribute:: periphs
      :value: []



   .. py:attribute:: extra_init
      :value: []



   .. py:method:: generate(out_dir)


   .. py:method:: add_periph(periph_type, name, address)


   .. py:method:: add_extra_init(asm)


   .. py:property:: soc_h


   .. py:property:: start


   .. py:property:: lds


