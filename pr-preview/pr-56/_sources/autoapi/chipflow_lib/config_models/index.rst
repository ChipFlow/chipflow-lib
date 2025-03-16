chipflow_lib.config_models
==========================

.. py:module:: chipflow_lib.config_models


Classes
-------

.. autoapisummary::

   chipflow_lib.config_models.PadConfig
   chipflow_lib.config_models.SiliconConfig
   chipflow_lib.config_models.StepsConfig
   chipflow_lib.config_models.ChipFlowConfig
   chipflow_lib.config_models.Config


Module Contents
---------------

.. py:class:: PadConfig(/, **data)

   Bases: :py:obj:`pydantic.BaseModel`


   Configuration for a pad in chipflow.toml.


   .. py:attribute:: type
      :type:  Literal['io', 'i', 'o', 'oe', 'clock', 'reset', 'power', 'ground']


   .. py:attribute:: loc
      :type:  str


   .. py:method:: validate_loc_format()

      Validate that the location is in the correct format.



   .. py:method:: validate_pad_dict(v, info)
      :classmethod:


      Custom validation for pad dicts from TOML that may not have all fields.



.. py:class:: SiliconConfig(/, **data)

   Bases: :py:obj:`pydantic.BaseModel`


   Configuration for silicon in chipflow.toml.


   .. py:attribute:: processes
      :type:  List[chipflow_lib.platforms.utils.Process]


   .. py:attribute:: package
      :type:  Literal['caravel', 'cf20', 'pga144']


   .. py:attribute:: pads
      :type:  Dict[str, PadConfig]


   .. py:attribute:: power
      :type:  Dict[str, PadConfig]


   .. py:attribute:: debug
      :type:  Optional[Dict[str, bool]]
      :value: None



   .. py:method:: validate_pad_dicts(v, info)
      :classmethod:


      Pre-process pad dictionaries to handle legacy format.



.. py:class:: StepsConfig(/, **data)

   Bases: :py:obj:`pydantic.BaseModel`


   Configuration for steps in chipflow.toml.


   .. py:attribute:: silicon
      :type:  str


.. py:class:: ChipFlowConfig(/, **data)

   Bases: :py:obj:`pydantic.BaseModel`


   Root configuration for chipflow.toml.


   .. py:attribute:: project_name
      :type:  Optional[str]
      :value: None



   .. py:attribute:: top
      :type:  Dict[str, Any]


   .. py:attribute:: steps
      :type:  StepsConfig


   .. py:attribute:: silicon
      :type:  SiliconConfig


   .. py:attribute:: clocks
      :type:  Optional[Dict[str, str]]
      :value: None



   .. py:attribute:: resets
      :type:  Optional[Dict[str, str]]
      :value: None



.. py:class:: Config(/, **data)

   Bases: :py:obj:`pydantic.BaseModel`


   Root configuration model for chipflow.toml.


   .. py:attribute:: chipflow
      :type:  ChipFlowConfig


