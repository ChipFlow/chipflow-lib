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

Wrapping an NDA hard macro
--------------------------

For third-party / NDA hard macros shipped as a LEF + Liberty + Verilog stub,
use :py:func:`chipflow.rtl.blackbox.load_blackbox_wrapper`. The macro is
declared in ``chipflow.toml`` by logical name, pointing at a
``*.blackbox.json`` produced by `macrostrip
<https://github.com/ChipFlow/macrostrip>`__:

.. code-block:: toml

   # chipflow.toml
   [chipflow.silicon.macros.sram_64x64]
   blackbox = "vendor/ihp/sram_64x64.blackbox.json"

.. code-block:: python

   from chipflow.rtl import load_blackbox_wrapper

   sram = load_blackbox_wrapper(
       "sram_64x64",
       clocks={"sys": "CLK"},
       resets={"sys": "RST_N"},
   )
   m.submodules.sram = sram

Signal pins become signature members (``In(width)`` / ``Out(width)``); power,
ground, clock, and reset pins are handled out-of-band. At submit time the
platform bundles the macro's companion files (LEF, Liberty, frame-view GDS,
Verilog stub, blackbox JSON) into a ``macros.tar.gz`` alongside the RTLIL, so
the ChipFlow backend can feed them to ORFS without the real macro layout ever
leaving customer premises.

Non-NDA macros
~~~~~~~~~~~~~~

The same mechanism works for macros you're free to ship in full — no NDA, no
stripping. Point ``macrostrip blackbox`` at the *real* GDS (rather than
running ``macrostrip frame`` first):

.. code-block:: bash

   macrostrip blackbox \
     --lef macro.lef --top MY_MACRO \
     --frame-gds macro.real.gds \
     --liberty macro.lib \
     --verilog-stub macro.v \
     -o macro.blackbox.json

Declare and instantiate it exactly as above. The blackbox JSON schema field
is named ``frame_gds`` for historical reasons, but chipflow-lib treats it as
"the GDS to include" — frame-view or real, the submission path is identical.
Skip ``macrostrip swap`` on return: there's nothing to substitute back.

API
---

- :py:class:`chipflow.rtl.wrapper.RTLWrapper` — the generated component.
- :py:func:`chipflow.rtl.wrapper.load_wrapper_from_toml` — loader that parses
  the TOML, runs any configured preprocessing, and returns an
  :py:class:`~chipflow.rtl.wrapper.RTLWrapper`.
- :py:class:`chipflow.rtl.wrapper.ExternalWrapConfig` — Pydantic schema for the
  TOML configuration.
- :py:func:`chipflow.rtl.blackbox.load_blackbox_wrapper` — loader for hard
  macros declared in ``[chipflow.silicon.macros]``.
- :py:class:`chipflow.rtl.blackbox.BlackboxWrapper` — the generated component
  for a hard macro; subclass of :py:class:`~chipflow.rtl.wrapper.RTLWrapper`.
