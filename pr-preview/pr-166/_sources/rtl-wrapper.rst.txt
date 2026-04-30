Wrapping External RTL
=====================

``chipflow.rtl.wrapper`` turns a TOML description of an external Verilog or
SystemVerilog module into an Amaranth :py:class:`~amaranth.lib.wiring.Component`
ready to drop into a design. The TOML specifies the source files, clocks and
resets, bus/pin interfaces, optional preprocessing (sv2v, yosys-slang,
SpinalHDL), and — as of this release — Verilog module ``parameter`` overrides.

This page is an API-level pointer. For the full usage guide, worked examples,
and the TOML reference, see the ChipFlow training material:

- `RTLWrapper: Wrapping External RTL via TOML <https://github.com/ChipFlow/chipflow-training/blob/main/rtl-wrapper.md>`__ — TOML reference, Wishbone-timer example, preprocessing.
- `Wrapping External RTL <https://github.com/ChipFlow/chipflow-training/blob/main/wrapping-external-rtl.md>`__ — manual ``Instance(...)`` path for simple modules.
- `Wrapping CV32E40P <https://github.com/ChipFlow/chipflow-training/blob/main/cv32e40p-example.md>`__ — a worked example with sv2v preprocessing.

Quick reference
---------------

Load a wrapper from a TOML file and instantiate it inside a design:

.. code-block:: python

   from chipflow.rtl.wrapper import load_wrapper_from_toml

   class MyDesign(wiring.Component):
       def elaborate(self, platform):
           m = Module()
           m.submodules.timer = load_wrapper_from_toml("wb_timer.toml")
           return m

Supply Verilog ``parameter`` overrides from TOML, from Python, or both (the
Python kwarg wins on collisions; unmentioned parameters fall back to the TOML
table):

.. code-block:: toml

   # wb_timer.toml
   name = "wb_timer"

   [parameters]
   DATA_WIDTH = 32
   ADDR_WIDTH = 4

.. code-block:: python

   # caller overrides DATA_WIDTH; ADDR_WIDTH=4 still applies
   w = load_wrapper_from_toml("wb_timer.toml", parameters={"DATA_WIDTH": 64})

The merged parameters are emitted as ``p_<NAME>=<value>`` kwargs on the
``Instance()`` at elaboration, and are also fed into generator template
substitution (so SpinalHDL / sv2v / yosys-slang see the final values when
producing Verilog).

API
---

- :py:class:`chipflow.rtl.wrapper.RTLWrapper` — the generated component.
- :py:func:`chipflow.rtl.wrapper.load_wrapper_from_toml` — loader that parses
  the TOML, runs any configured preprocessing, and returns an
  :py:class:`~chipflow.rtl.wrapper.RTLWrapper`.
- :py:class:`chipflow.rtl.wrapper.ExternalWrapConfig` — Pydantic schema for the
  TOML configuration.
