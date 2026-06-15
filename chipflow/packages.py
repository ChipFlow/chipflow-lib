# SPDX-License-Identifier: BSD-2-Clause
"""
Package definitions for ChipFlow platforms.

This module contains package type definitions for supported IC packages.
"""

from .packaging import QuadPackageDef, BareDiePackageDef, GAPackageDef, Package, OpenframePackageDef

# Add any new package types to both PACKAGE_DEFINITIONS and the PackageDef union.
# Europractice quad packages use the QuadPackageDef pin numbering (CCW from
# top-left) which matches EP's GDS labels. EP-specific cell names, layer
# conventions and pin_map strings live in chipflow-backend's packaging_klayout
# plugin (data/ep_packages.json), keeping this library vendor-agnostic.
PACKAGE_DEFINITIONS = {
    # Bare die / generic
    "cf20":      BareDiePackageDef(name="cf20",      width=7,  height=3),
    "openframe": OpenframePackageDef(),

    # PGA — perimeter pin grid arrays
    "pga84":     QuadPackageDef(name="pga84",   width=21, height=21),
    "pga100s":   QuadPackageDef(name="pga100s", width=25, height=25),
    "pga100l":   QuadPackageDef(name="pga100l", width=25, height=25),
    "pga120":    QuadPackageDef(name="pga120",  width=30, height=30),
    "pga144":    QuadPackageDef(name="pga144",  width=36, height=36),
    "pga208":    QuadPackageDef(name="pga208",  width=52, height=52),
    # pga256 — staggered double-row, deferred (see ep_packages.json _todo_v2_)

    # QFP / CERQUAD
    "qfp64":     QuadPackageDef(name="qfp64",   width=16, height=16),
    "qfp120":    QuadPackageDef(name="qfp120",  width=30, height=30),
    "qfp160":    QuadPackageDef(name="qfp160",  width=40, height=40),
    "qfp208":    QuadPackageDef(name="qfp208",  width=52, height=52),

    # QFN — QuadPackageDef requires height // 2 > 3 (min 8 pins/side) for its
    # bringup power-pin allocation, so qfn16 and qfn24 are intentionally absent.
    # Their EP descriptors remain in ep_packages.json for documentation.
    "qfn32":         QuadPackageDef(name="qfn32",        width=8,  height=8),
    "qfn40_6x6":     QuadPackageDef(name="qfn40_6x6",    width=10, height=10),
    "qfn48":         QuadPackageDef(name="qfn48",        width=12, height=12),
    "qfn56":         QuadPackageDef(name="qfn56",        width=14, height=14),
    "qfn64_9x9":     QuadPackageDef(name="qfn64_9x9",    width=16, height=16),
    "qfn80_12x12":   QuadPackageDef(name="qfn80_12x12",  width=20, height=20),
    "qfn88_10x10":   QuadPackageDef(name="qfn88_10x10",  width=22, height=22),
    "qfn100_12x12":  QuadPackageDef(name="qfn100_12x12", width=25, height=25),

    # BGA — ball grid array (different geometry class)
    "bga144":    GAPackageDef(name="bga144", width=36, height=36),
}

Package.model_rebuild()
