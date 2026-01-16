# SPDX-License-Identifier: BSD-2-Clause
"""CXXRTL C API bindings via ctypes.

This module provides Python bindings for the CXXRTL simulation engine,
allowing fast compiled simulation of HDL designs with Python testbenches.
"""

import ctypes
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    c_char_p,
    c_int,
    c_size_t,
    c_uint32,
    c_void_p,
)
from pathlib import Path
from typing import Dict, Iterator, Tuple, Union


# CXXRTL object types
class CxxrtlType:
    VALUE = 0
    WIRE = 1
    MEMORY = 2
    ALIAS = 3
    OUTLINE = 4


# CXXRTL object flags
class CxxrtlFlag:
    INPUT = 1 << 0
    OUTPUT = 1 << 1
    INOUT = INPUT | OUTPUT
    DRIVEN_SYNC = 1 << 2
    DRIVEN_COMB = 1 << 3
    UNDRIVEN = 1 << 4


class CxxrtlObject(Structure):
    """CXXRTL object descriptor - matches struct cxxrtl_object in cxxrtl_capi.h"""

    _fields_ = [
        ("type", c_uint32),
        ("flags", c_uint32),
        ("width", c_size_t),
        ("lsb_at", c_size_t),
        ("depth", c_size_t),
        ("zero_at", c_size_t),
        ("curr", POINTER(c_uint32)),
        ("next", POINTER(c_uint32)),
        ("outline", c_void_p),
        ("attrs", c_void_p),
    ]


# Callback type for cxxrtl_enum
EnumCallback = CFUNCTYPE(
    None, c_void_p, c_char_p, POINTER(CxxrtlObject), c_size_t
)


class CxxrtlSimulator:
    """Python wrapper for CXXRTL simulation.

    This class provides a Pythonic interface to CXXRTL compiled simulations,
    supporting signal access, stepping, and VCD tracing.

    Example::

        sim = CxxrtlSimulator("build/design.so", "design")
        sim.reset()

        # Clock cycle
        sim.set("clk", 0)
        sim.step()
        sim.set("clk", 1)
        sim.step()

        # Read output
        value = sim.get("data_out")
    """

    def __init__(self, library_path: Union[str, Path], top_module: str):
        """Initialize CXXRTL simulator.

        Args:
            library_path: Path to compiled CXXRTL shared library (.so/.dylib)
            top_module: Name of the top-level module (used to find create function)
        """
        self._lib_path = Path(library_path)
        self._top_module = top_module
        self._lib: ctypes.CDLL
        self._handle: c_void_p
        self._objects: Dict[str, CxxrtlObject] = {}

        self._load_library()
        self._create_handle()
        self._discover_objects()

    def _load_library(self) -> None:
        """Load the CXXRTL shared library and set up function prototypes."""
        if not self._lib_path.exists():
            raise FileNotFoundError(f"CXXRTL library not found: {self._lib_path}")

        self._lib = ctypes.CDLL(str(self._lib_path))

        # cxxrtl_toplevel <top>_create()
        create_name = f"{self._top_module}_create"
        if not hasattr(self._lib, create_name):
            raise RuntimeError(
                f"Library does not export {create_name}. "
                f"Make sure the library was compiled with top module '{self._top_module}'"
            )
        self._toplevel_create = getattr(self._lib, create_name)
        self._toplevel_create.restype = c_void_p
        self._toplevel_create.argtypes = []

        # cxxrtl_handle cxxrtl_create(cxxrtl_toplevel)
        self._lib.cxxrtl_create.restype = c_void_p
        self._lib.cxxrtl_create.argtypes = [c_void_p]

        # void cxxrtl_destroy(cxxrtl_handle)
        self._lib.cxxrtl_destroy.restype = None
        self._lib.cxxrtl_destroy.argtypes = [c_void_p]

        # void cxxrtl_reset(cxxrtl_handle)
        self._lib.cxxrtl_reset.restype = None
        self._lib.cxxrtl_reset.argtypes = [c_void_p]

        # int cxxrtl_eval(cxxrtl_handle)
        self._lib.cxxrtl_eval.restype = c_int
        self._lib.cxxrtl_eval.argtypes = [c_void_p]

        # int cxxrtl_commit(cxxrtl_handle)
        self._lib.cxxrtl_commit.restype = c_int
        self._lib.cxxrtl_commit.argtypes = [c_void_p]

        # size_t cxxrtl_step(cxxrtl_handle)
        self._lib.cxxrtl_step.restype = c_size_t
        self._lib.cxxrtl_step.argtypes = [c_void_p]

        # struct cxxrtl_object *cxxrtl_get_parts(cxxrtl_handle, const char*, size_t*)
        # Note: cxxrtl_get is an inline function in the header, we use cxxrtl_get_parts
        self._lib.cxxrtl_get_parts.restype = POINTER(CxxrtlObject)
        self._lib.cxxrtl_get_parts.argtypes = [c_void_p, c_char_p, POINTER(c_size_t)]

        # void cxxrtl_enum(cxxrtl_handle, void*, callback)
        self._lib.cxxrtl_enum.restype = None
        self._lib.cxxrtl_enum.argtypes = [c_void_p, c_void_p, EnumCallback]

    def _create_handle(self) -> None:
        """Create the CXXRTL simulation handle."""
        toplevel = self._toplevel_create()
        if not toplevel:
            raise RuntimeError("Failed to create CXXRTL toplevel")

        self._handle = self._lib.cxxrtl_create(toplevel)
        if not self._handle:
            raise RuntimeError("Failed to create CXXRTL handle")

    def _discover_objects(self) -> None:
        """Enumerate all objects in the design and cache them."""
        self._objects.clear()
        names: list[str] = []

        @EnumCallback
        def callback(data, name, obj, parts):
            name_str = name.decode("utf-8")
            names.append(name_str)

        self._lib.cxxrtl_enum(self._handle, None, callback)

        # Now fetch each object individually using cxxrtl_get_parts
        for name in names:
            parts = c_size_t(0)
            obj_ptr = self._lib.cxxrtl_get_parts(
                self._handle, name.encode("utf-8"), ctypes.byref(parts)
            )
            # Only store single-part objects (like cxxrtl_get does)
            if obj_ptr and parts.value == 1:
                self._objects[name] = obj_ptr.contents

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        self._lib.cxxrtl_reset(self._handle)

    def eval(self) -> bool:
        """Evaluate combinatorial logic.

        Returns:
            True if the design converged immediately
        """
        return bool(self._lib.cxxrtl_eval(self._handle))

    def commit(self) -> bool:
        """Commit sequential state.

        Returns:
            True if any state changed
        """
        return bool(self._lib.cxxrtl_commit(self._handle))

    def step(self) -> int:
        """Simulate to a fixed point (eval + commit until stable).

        Returns:
            Number of delta cycles
        """
        return self._lib.cxxrtl_step(self._handle)

    def get(self, name: str) -> int:
        """Get the current value of a signal.

        Args:
            name: Signal name (e.g., "i_clk" or "o_data")

        Returns:
            Current value as an integer
        """
        obj = self._get_object(name)
        return self._read_value(obj)

    def set(self, name: str, value: int) -> None:
        """Set the next value of a signal.

        Args:
            name: Hierarchical signal name
            value: Value to set
        """
        obj = self._get_object(name)
        self._write_value(obj, value)

    def _get_object(self, name: str) -> CxxrtlObject:
        """Get object by name, with caching."""
        if name in self._objects:
            return self._objects[name]

        # Try fetching directly using cxxrtl_get_parts
        parts = c_size_t(0)
        obj_ptr = self._lib.cxxrtl_get_parts(
            self._handle, name.encode("utf-8"), ctypes.byref(parts)
        )
        if not obj_ptr or parts.value != 1:
            raise KeyError(f"Signal not found: {name}")

        self._objects[name] = obj_ptr.contents
        return self._objects[name]

    def _read_value(self, obj: CxxrtlObject) -> int:
        """Read value from object's curr buffer."""
        if not obj.curr:
            return 0

        num_chunks = (obj.width + 31) // 32
        value = 0
        for i in range(num_chunks):
            value |= obj.curr[i] << (i * 32)

        # Mask to actual width
        if obj.width < 64:
            value &= (1 << obj.width) - 1

        return value

    def _write_value(self, obj: CxxrtlObject, value: int) -> None:
        """Write value to object's next buffer."""
        if not obj.next:
            raise RuntimeError(
                f"Cannot write to read-only object (type={obj.type}, flags={obj.flags})"
            )

        num_chunks = (obj.width + 31) // 32
        for i in range(num_chunks):
            obj.next[i] = (value >> (i * 32)) & 0xFFFFFFFF

    def signals(self) -> Iterator[Tuple[str, CxxrtlObject]]:
        """Iterate over all signals in the design.

        Yields:
            Tuples of (name, object) for each signal
        """
        yield from self._objects.items()

    def inputs(self) -> Iterator[Tuple[str, CxxrtlObject]]:
        """Iterate over input signals."""
        for name, obj in self._objects.items():
            if obj.flags & CxxrtlFlag.INPUT:
                yield name, obj

    def outputs(self) -> Iterator[Tuple[str, CxxrtlObject]]:
        """Iterate over output signals."""
        for name, obj in self._objects.items():
            if obj.flags & CxxrtlFlag.OUTPUT:
                yield name, obj

    def close(self) -> None:
        """Release simulation resources."""
        if hasattr(self, "_handle") and hasattr(self, "_lib"):
            self._lib.cxxrtl_destroy(self._handle)
            del self._handle

    def __enter__(self) -> "CxxrtlSimulator":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
