# SPDX-License-Identifier: BSD-2-Clause
"""Blackbox macro wrapper.

``load_blackbox_wrapper`` reads a ``*.blackbox.json`` produced by
`macrostrip <https://github.com/ChipFlow/macrostrip>`_ (or any conformant
tool) and returns an :class:`RTLWrapper` subclass that:

- synthesizes an :class:`ExternalWrapConfig` from the JSON's pin list,
- uses the companion Verilog stub so Yosys sees the macro's port
  signature during synthesis,
- registers the macro with the platform at elaborate time so the submit
  step can bundle its LEF / Liberty / frame-view GDS into the upload.

The macro is declared in ``chipflow.toml``::

    [chipflow.silicon.macros.sram_64x64]
    blackbox = "vendor/ihp/sram_64x64.blackbox.json"

and instantiated from Python by logical name::

    sram = load_blackbox_wrapper("sram_64x64",
                                 clocks={"sys": "CLK"},
                                 resets={"sys": "RST_N"})
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from chipflow import ChipFlowError

from .wrapper import ExternalWrapConfig, Files, Port, RTLWrapper


__all__ = ["load_blackbox_wrapper", "BlackboxWrapper"]


def _build_port_configs(
    macro_name: str,
    pins: list[dict],
    clock_pins: set[str],
    reset_pins: set[str],
) -> Dict[str, Port]:
    """Translate blackbox JSON pins into RTLWrapper ``Port`` entries.

    Power/ground pins are skipped (handled at the platform/PDN level,
    not wired from Amaranth). Clock and reset pins are skipped here
    because they're wired via ``config.clocks`` / ``config.resets``.
    ``inout`` signal pins (non power/ground) are rejected — pin-style
    bidirectional wrapping isn't automated yet.
    """
    ports: Dict[str, Port] = {}
    for pin in pins:
        name = pin["name"]
        role = pin.get("role", "signal")
        direction = pin["direction"]
        width = int(pin["width"])

        if role in ("power", "ground"):
            continue
        if name in clock_pins or name in reset_pins:
            continue

        if direction == "inout":
            raise ChipFlowError(
                f"Macro '{macro_name}': pin '{name}' is inout and "
                "cannot be auto-wrapped. Declare it explicitly as a "
                "pin-style interface or omit it from the blackbox."
            )
        if direction not in ("in", "out"):
            raise ChipFlowError(
                f"Macro '{macro_name}': pin '{name}' has unknown "
                f"direction {direction!r}"
            )

        iface_cls = "In" if direction == "in" else "Out"
        verilog_prefix = "i_" if direction == "in" else "o_"
        ports[name] = Port(
            interface=f"amaranth.lib.wiring.{iface_cls}({width})",
            map=f"{verilog_prefix}{name}",
        )
    return ports


class BlackboxWrapper(RTLWrapper):
    """RTLWrapper subclass that also registers the macro with the platform.

    Shares all wrapper behaviour with :class:`RTLWrapper`; the only
    difference is that :meth:`elaborate` informs the platform about the
    macro's physical artifacts (LEF / Liberty / frame-view GDS) so the
    submit step can bundle them.
    """

    def __init__(
        self,
        config: ExternalWrapConfig,
        verilog_files: list[Path],
        logical_name: str,
    ):
        super().__init__(config, verilog_files)
        self._logical_name = logical_name

    def elaborate(self, platform):
        if platform is not None and hasattr(platform, "add_macro"):
            platform.add_macro(self._logical_name)
        return super().elaborate(platform)


def load_blackbox_wrapper(
    logical_name: str,
    *,
    clocks: Optional[Dict[str, str]] = None,
    resets: Optional[Dict[str, str]] = None,
) -> BlackboxWrapper:
    """Load a hard macro by logical name declared in ``chipflow.toml``.

    Args:
        logical_name: Key under ``[chipflow.silicon.macros]``.
        clocks: Amaranth clock-domain → macro pin name. e.g.
            ``{"sys": "CLK"}`` wires the ``sys`` domain's clock to the
            macro's LEF pin ``CLK``.
        resets: Amaranth clock-domain → macro reset pin name (active-low
            convention, matching :class:`RTLWrapper`).

    Returns:
        A :class:`BlackboxWrapper` (a :class:`wiring.Component`) whose
        signature mirrors the macro's signal pins. Power/ground pins
        are omitted; clock/reset pins are omitted from the signature
        and wired at elaborate time.

    Raises:
        ChipFlowError: if the macro isn't declared in ``chipflow.toml``,
            its blackbox JSON is missing/malformed, or a referenced
            clock/reset pin isn't in the macro's pin list.
    """
    clocks = dict(clocks or {})
    resets = dict(resets or {})

    # Parse chipflow.toml and locate the declared macro.
    from ..config.parser import _parse_config
    from ..utils import ensure_chipflow_root

    cfg = _parse_config()
    if not cfg.chipflow.silicon:
        raise ChipFlowError(
            "load_blackbox_wrapper requires a [chipflow.silicon] section"
        )
    macros_cfg = cfg.chipflow.silicon.macros
    if logical_name not in macros_cfg:
        raise ChipFlowError(
            f"Macro '{logical_name}' is not declared in "
            f"[chipflow.silicon.macros]. Known: "
            f"{sorted(macros_cfg.keys()) or '(none)'}"
        )

    root = ensure_chipflow_root()
    bb_path = Path(macros_cfg[logical_name].blackbox)
    if not bb_path.is_absolute():
        bb_path = (root / bb_path).resolve()

    try:
        bb = json.loads(bb_path.read_text())
    except FileNotFoundError:
        raise ChipFlowError(
            f"Macro '{logical_name}': blackbox JSON not found at {bb_path}"
        )
    except json.JSONDecodeError as e:
        raise ChipFlowError(
            f"Macro '{logical_name}': invalid JSON in {bb_path}: {e}"
        )

    if bb.get("version") != "1":
        raise ChipFlowError(
            f"Macro '{logical_name}': unsupported blackbox JSON version "
            f"{bb.get('version')!r} (expected '1')"
        )

    macro_cell_name = bb["name"]
    pins = bb.get("pins", [])
    pin_names = {p["name"] for p in pins}

    for domain, pin_name in clocks.items():
        if pin_name not in pin_names:
            raise ChipFlowError(
                f"Macro '{logical_name}': clock pin '{pin_name}' "
                f"(domain '{domain}') not found. Pins: {sorted(pin_names)}"
            )
    for domain, pin_name in resets.items():
        if pin_name not in pin_names:
            raise ChipFlowError(
                f"Macro '{logical_name}': reset pin '{pin_name}' "
                f"(domain '{domain}') not found. Pins: {sorted(pin_names)}"
            )

    clock_pins = set(clocks.values())
    reset_pins = set(resets.values())

    port_configs = _build_port_configs(
        macro_cell_name, pins, clock_pins, reset_pins
    )

    # The Verilog stub is needed by Yosys so the black-box Instance has
    # a proper port signature during synthesis. It's optional — some
    # flows might pre-supply the stub another way — but when present,
    # pass it through the regular add_file path at elaborate.
    verilog_files: list[Path] = []
    stub_rel = (bb.get("files") or {}).get("verilog_stub")
    if stub_rel is not None:
        stub_path = (bb_path.parent / stub_rel).resolve()
        if not stub_path.exists():
            raise ChipFlowError(
                f"Macro '{logical_name}': verilog_stub '{stub_rel}' "
                f"(resolved to {stub_path}) not found"
            )
        verilog_files.append(stub_path)

    # Files.path is required by the Pydantic model but the constructor
    # path below doesn't use it for source discovery — we pass
    # verilog_files explicitly.
    config = ExternalWrapConfig(
        name=macro_cell_name,
        files=Files(path=bb_path.parent),
        clocks=clocks,
        resets=resets,
        ports=port_configs,
    )
    return BlackboxWrapper(config, verilog_files, logical_name)
