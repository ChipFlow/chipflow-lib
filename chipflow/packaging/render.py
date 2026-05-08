# SPDX-License-Identifier: BSD-2-Clause
"""
Renderers for ``pins.lock`` — text table and SVG layout.

Used by ``chipflow pin show``. The text view works for any package
type. The SVG view is currently implemented for perimeter-pin packages
(:class:`QuadPackageDef`, :class:`BlockPackageDef`); other types raise
:class:`ChipFlowError` and are expected to fall back to the text view.
"""

from html import escape
from typing import Dict, Tuple

from .. import ChipFlowError
from .lockfile import LockFile
from .standard import BlockPackageDef, QuadPackageDef


def _walk_ports(lockfile: LockFile):
    """Yield (component, interface, port_name, bit, pin, port_desc) for
    every assigned pin in the lockfile."""
    for cname, comp in lockfile.port_map.ports.items():
        for iname, intf in comp.items():
            for pname, port in intf.items():
                if port.pins is None:
                    continue
                for bit, pin in enumerate(port.pins):
                    yield cname, iname, pname, bit, pin, port


def _slot_label(cname: str, iname: str, pname: str, bit: int, width: int) -> str:
    if width > 1:
        return f"{cname}.{iname}.{pname}[{bit}]"
    return f"{cname}.{iname}.{pname}"


def render_text(lockfile: LockFile) -> str:
    """Render the pin allocation as a sorted text table."""
    rows = []
    for cname, iname, pname, bit, pin, port in _walk_ports(lockfile):
        label = _slot_label(cname, iname, pname, bit, len(port.pins or []))
        direction = port.iomodel.get('direction', '')
        # io.Direction uses 'i'/'o'/'io' as its short value form.
        dir_str = getattr(direction, 'value', str(direction))
        rows.append((pin, label, port.type, dir_str))

    def _sortkey(row):
        p = row[0]
        return (0, p) if isinstance(p, int) else (1, repr(p))

    rows.sort(key=_sortkey)

    out = ["{:<8} {:<8} {:<5} {}".format("PIN", "TYPE", "DIR", "PORT")]
    for pin, label, kind, direction in rows:
        out.append("{:<8} {:<8} {:<5} {}".format(str(pin), kind, direction, label))
    return "\n".join(out) + "\n"


def _pin_to_perimeter_position(pin: int, width: int, height: int) -> Tuple[str, int]:
    """Map a perimeter pin number to ``(side, slot)``.

    Convention shared by :class:`QuadPackageDef` and
    :class:`BlockPackageDef`: pin 1 sits at the top of the West edge,
    numbering proceeds counter-clockwise. ``slot`` is 0-indexed along
    the side in the direction of numbering (top→bottom on W/E in
    natural progression, left→right on S, right→left on N).
    """
    p = pin
    if p <= height:
        return 'W', p - 1
    p -= height
    if p <= width:
        return 'S', p - 1
    p -= width
    if p <= height:
        return 'E', p - 1
    p -= height
    return 'N', p - 1


def _perimeter_svg(width: int, height: int,
                   pin_labels: Dict[int, str], title: str) -> str:
    """Render a perimeter package layout as standalone SVG.

    N/S labels are rotated and extend OUTWARD from the package; W/E
    labels are horizontal and extend outward from the side. Canvas
    padding scales with the longest label so nothing gets clipped.
    """
    pitch = 30
    # Approximate per-character width for 11px monospace.
    char_px = 6.6
    longest_label = max((len(s) for s in pin_labels.values()), default=4)
    label_run = int(longest_label * char_px) + 16

    # Side margins: enough for horizontal W/E labels + a small gap.
    pad_x = label_run + 40
    # Top/bottom margins: enough for rotated N/S labels + title strip.
    pad_y = label_run + 60

    box_w = width * pitch
    box_h = height * pitch
    svg_w = box_w + 2 * pad_x
    svg_h = box_h + 2 * pad_y

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}">'
    )
    parts.append(
        '<style>'
        '.pkg{fill:#fafafa;stroke:#222;stroke-width:1.5}'
        '.tick{stroke:#666;stroke-width:1}'
        '.lbl{font:11px monospace;fill:#222}'
        '.pin{font:10px monospace;fill:#888}'
        '.title{font:14px sans-serif;fill:#222}'
        '</style>'
    )
    parts.append(
        f'<text class="title" x="{svg_w / 2}" y="24" '
        f'text-anchor="middle">{escape(title)}</text>'
    )
    parts.append(
        f'<rect class="pkg" x="{pad_x}" y="{pad_y}" '
        f'width="{box_w}" height="{box_h}"/>'
    )

    total = 2 * (width + height)
    for pin in range(1, total + 1):
        side, slot = _pin_to_perimeter_position(pin, width, height)
        label = escape(pin_labels.get(pin, '—'))  # em dash for empty

        if side == 'W':
            cx, cy = pad_x, pad_y + (slot + 0.5) * pitch
            parts.append(
                f'<line class="tick" x1="{cx - 8}" y1="{cy}" '
                f'x2="{cx}" y2="{cy}"/>'
            )
            parts.append(
                f'<text class="pin" x="{cx - 12}" y="{cy + 4}" '
                f'text-anchor="end">{pin}</text>'
            )
            parts.append(
                f'<text class="lbl" x="{cx - 32}" y="{cy + 4}" '
                f'text-anchor="end">{label}</text>'
            )
        elif side == 'E':
            cx = pad_x + box_w
            cy = pad_y + box_h - (slot + 0.5) * pitch
            parts.append(
                f'<line class="tick" x1="{cx}" y1="{cy}" '
                f'x2="{cx + 8}" y2="{cy}"/>'
            )
            parts.append(
                f'<text class="pin" x="{cx + 12}" y="{cy + 4}" '
                f'text-anchor="start">{pin}</text>'
            )
            parts.append(
                f'<text class="lbl" x="{cx + 32}" y="{cy + 4}" '
                f'text-anchor="start">{label}</text>'
            )
        elif side == 'N':
            # rotate(-90) + text-anchor="start": glyphs extend in +x
            # pre-rotation; after a -90° (CCW) rotation about the
            # anchor, they extend upward — away from the block top.
            cx, cy = pad_x + box_w - (slot + 0.5) * pitch, pad_y
            parts.append(
                f'<line class="tick" x1="{cx}" y1="{cy - 8}" '
                f'x2="{cx}" y2="{cy}"/>'
            )
            parts.append(
                f'<text class="pin" x="{cx}" y="{cy - 12}" '
                f'text-anchor="middle">{pin}</text>'
            )
            anchor_x, anchor_y = cx + 3, cy - 28
            parts.append(
                f'<text class="lbl" x="{anchor_x}" y="{anchor_y}" '
                f'text-anchor="start" '
                f'transform="rotate(-90 {anchor_x} {anchor_y})">{label}</text>'
            )
        else:  # 'S'
            # rotate(90) + text-anchor="start": glyphs extend in +x
            # pre-rotation; after a +90° (CW) rotation about the anchor,
            # they extend downward — away from the block bottom.
            cx = pad_x + (slot + 0.5) * pitch
            cy = pad_y + box_h
            parts.append(
                f'<line class="tick" x1="{cx}" y1="{cy}" '
                f'x2="{cx}" y2="{cy + 8}"/>'
            )
            parts.append(
                f'<text class="pin" x="{cx}" y="{cy + 20}" '
                f'text-anchor="middle">{pin}</text>'
            )
            anchor_x, anchor_y = cx - 3, cy + 28
            parts.append(
                f'<text class="lbl" x="{anchor_x}" y="{anchor_y}" '
                f'text-anchor="start" '
                f'transform="rotate(90 {anchor_x} {anchor_y})">{label}</text>'
            )

    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_svg(lockfile: LockFile) -> str:
    """Render the pin allocation as SVG.

    Currently supports :class:`QuadPackageDef` and
    :class:`BlockPackageDef`. Other package types raise
    :class:`ChipFlowError`.
    """
    pkg = lockfile.package.package_type
    if not isinstance(pkg, (QuadPackageDef, BlockPackageDef)):
        raise ChipFlowError(
            f"SVG output is not yet supported for "
            f"{type(pkg).__name__}. Use --format text."
        )

    pin_labels: Dict[int, str] = {}
    for cname, iname, pname, bit, pin, port in _walk_ports(lockfile):
        if not isinstance(pin, int):
            continue
        pin_labels[pin] = _slot_label(
            cname, iname, pname, bit, len(port.pins or [])
        )

    title = f"{pkg.name} ({type(pkg).__name__} {pkg.width}×{pkg.height})"
    return _perimeter_svg(pkg.width, pkg.height, pin_labels, title)
