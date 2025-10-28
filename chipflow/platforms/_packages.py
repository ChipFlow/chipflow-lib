from ..packaging import QuadPackageDef, BareDiePackageDef, GAPackageDef, Package, OpenframePackageDef

# Add any new package types to both PACKAGE_DEFINITIONS and the PackageDef union
PACKAGE_DEFINITIONS = {
    "pga144": QuadPackageDef(name="pga144", width=36, height=36),
    "cf20": BareDiePackageDef(name="cf20", width=7, height=3),
    "bga144": GAPackageDef(name="bga144", width=36, height=36),
    "openframe": OpenframePackageDef()
}

Package.model_rebuild()
