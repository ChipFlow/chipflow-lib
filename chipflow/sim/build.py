# SPDX-License-Identifier: BSD-2-Clause
"""Build CXXRTL shared libraries from HDL sources.

This module provides functions to compile Amaranth, Verilog, and SystemVerilog
designs into CXXRTL shared libraries for fast simulation.
"""

import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence, Union

logger = logging.getLogger(__name__)


def _find_zig_cxx() -> Optional[list[str]]:
    """Find zig C++ compiler.

    Returns command list for zig c++, or None if not available.
    """
    # Prefer zig via ziglang package (consistent cross-platform builds)
    try:
        import ziglang  # noqa: F401

        return [sys.executable, "-m", "ziglang", "c++"]
    except ImportError:
        pass

    # Fall back to system zig
    if shutil.which("zig"):
        return ["zig", "c++"]

    return None


def _find_system_linker() -> list[str]:
    """Find a system linker for creating shared libraries."""
    for linker in ["c++", "g++", "clang++"]:
        if shutil.which(linker):
            return [linker]
    raise RuntimeError("No C++ linker found. Install g++ or clang++.")


def _get_shared_lib_extension() -> str:
    """Get platform-specific shared library extension."""
    system = platform.system()
    if system == "Darwin":
        return ".dylib"
    elif system == "Windows":
        return ".dll"
    else:
        return ".so"


def _get_cxxrtl_include_path() -> Path:
    """Find CXXRTL runtime headers.

    Checks yowasp-yosys share directory and homebrew yosys installation.
    """
    # Try yowasp-yosys first
    try:
        import yowasp_yosys

        yowasp_dir = Path(yowasp_yosys.__file__).parent
        share_dir = yowasp_dir / "share" / "include" / "backends" / "cxxrtl" / "runtime"
        if share_dir.exists():
            return share_dir
    except ImportError:
        pass

    # Try homebrew yosys (macOS)
    homebrew_path = Path("/opt/homebrew/opt/yosys/share/yosys/include/backends/cxxrtl/runtime")
    if homebrew_path.exists():
        return homebrew_path

    # Try system yosys
    system_path = Path("/usr/share/yosys/include/backends/cxxrtl/runtime")
    if system_path.exists():
        return system_path

    raise RuntimeError(
        "Could not find CXXRTL headers. Install yowasp-yosys or yosys."
    )


def _run_yosys(commands: str) -> None:
    """Run Yosys with the given commands.

    Uses yowasp-yosys if available, otherwise native yosys.
    Note: All paths in commands must be absolute since yowasp-yosys
    doesn't support cwd parameter.
    """
    try:
        from yowasp_yosys import run_yosys

        logger.debug("Using yowasp-yosys")
        result = run_yosys(["-p", commands])
        if result != 0:
            raise RuntimeError(f"yowasp-yosys failed with exit code {result}")
    except ImportError:
        logger.debug("Using native yosys")
        yosys = shutil.which("yosys")
        if not yosys:
            raise RuntimeError("Neither yowasp-yosys nor native yosys found")

        result = subprocess.run(
            [yosys, "-p", commands],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"yosys failed: {result.stderr}")


def _generate_capi_wrapper(cxxrtl_cc_path: Path, wrapper_path: Path, top_module: str) -> None:
    """Generate a C API wrapper that exports the toplevel create function.

    The CXXRTL C API requires a `<top>_create()` function to be provided by the user.
    This generates a wrapper that includes the CXXRTL code and exports the function.
    """
    # Convert module name to valid C++ identifier
    # CXXRTL naming convention:
    # - Adds "p_" prefix
    # - Replaces backslash with nothing
    # - Replaces space with "__"
    # - Replaces single underscore with "__" (double underscore)
    cpp_class_name = "p_" + top_module.replace("\\", "").replace(" ", "__").replace("_", "__")

    wrapper_code = f'''// Auto-generated CXXRTL C API wrapper
// This file provides the C API entry point for the {top_module} module

#include "{cxxrtl_cc_path.name}"

extern "C" {{

// Create function required by CXXRTL C API
cxxrtl_toplevel {top_module}_create() {{
    return new _cxxrtl_toplevel {{ std::make_unique<cxxrtl_design::{cpp_class_name}>() }};
}}

}}  // extern "C"
'''
    wrapper_path.write_text(wrapper_code)
    logger.debug(f"Generated C API wrapper: {wrapper_path}")


def build_cxxrtl(
    sources: Sequence[Union[str, Path]],
    top_module: str,
    output_dir: Union[str, Path],
    output_name: Optional[str] = None,
    include_dirs: Optional[Sequence[Union[str, Path]]] = None,
    defines: Optional[dict[str, str]] = None,
    optimization: str = "-O2",
    debug_info: bool = True,
) -> Path:
    """Build a CXXRTL shared library from HDL sources.

    Args:
        sources: List of Verilog/SystemVerilog source files
        top_module: Name of the top-level module
        output_dir: Directory for build artifacts
        output_name: Name for output library (default: top_module)
        include_dirs: Additional include directories for Verilog
        defines: Verilog preprocessor defines
        optimization: C++ optimization level (default: -O2)
        debug_info: Include CXXRTL debug info (default: True)

    Returns:
        Path to the compiled shared library
    """
    output_dir = Path(output_dir).absolute()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_name = output_name or top_module
    lib_ext = _get_shared_lib_extension()
    lib_path = output_dir / f"{output_name}{lib_ext}"
    cc_path = output_dir / f"{output_name}_cxxrtl.cc"

    # Build Yosys commands
    yosys_cmds = []

    # Read sources - use slang for .sv files, read_verilog for .v
    # Use absolute paths since yowasp-yosys doesn't support cwd
    for source in sources:
        source = Path(source).absolute()
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if source.suffix == ".sv":
            yosys_cmds.append(f"read_slang {source}")
        else:
            yosys_cmds.append(f"read_verilog {source}")

    # Set top module and elaborate
    yosys_cmds.append(f"hierarchy -top {top_module}")

    # Write CXXRTL
    cxxrtl_opts = []
    if debug_info:
        cxxrtl_opts.append("-g3")  # Maximum debug info

    yosys_cmds.append(f"write_cxxrtl {' '.join(cxxrtl_opts)} {cc_path}")

    # Run Yosys
    logger.info(f"Generating CXXRTL for {top_module}")
    _run_yosys("\n".join(yosys_cmds))

    if not cc_path.exists():
        raise RuntimeError(f"CXXRTL generation failed - {cc_path} not created")

    # Generate C API wrapper that exports the create function
    wrapper_path = output_dir / f"{output_name}_capi_wrapper.cc"
    _generate_capi_wrapper(cc_path, wrapper_path, top_module)

    # Find CXXRTL headers
    cxxrtl_include = _get_cxxrtl_include_path()
    logger.debug(f"Using CXXRTL headers from {cxxrtl_include}")

    # Compile to shared library
    # On macOS: use zig for compilation (consistent builds), system linker for linking
    # On Linux: use system compiler directly (zig uses libc++ which isn't always available)
    zig_cxx = _find_zig_cxx() if platform.system() == "Darwin" else None
    obj_path = output_dir / f"{output_name}_capi_wrapper.o"

    if zig_cxx:
        # macOS: Compile to object file with zig, link with system linker
        compile_cmd = [
            *zig_cxx,
            "-std=c++17",
            optimization,
            "-fPIC",
            "-c",
            f"-I{cxxrtl_include}",
            f"-I{output_dir}",
            "-DCXXRTL_INCLUDE_CAPI_IMPL",
            "-o", str(obj_path),
            str(wrapper_path),
        ]

        logger.info(f"Compiling CXXRTL with zig: {obj_path}")
        logger.debug(f"Compile command: {' '.join(compile_cmd)}")

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"C++ compilation failed: {result.stderr}")

        # Link with system linker
        linker = _find_system_linker()
        link_cmd = [
            *linker,
            "-shared",
            "-o", str(lib_path),
            str(obj_path),
            "-undefined", "dynamic_lookup",
        ]

        logger.info(f"Linking CXXRTL library: {lib_path}")
        logger.debug(f"Link command: {' '.join(link_cmd)}")

        result = subprocess.run(link_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Linking failed: {result.stderr}")
    else:
        # Fall back to system compiler for everything
        linker = _find_system_linker()
        compile_cmd = [
            *linker,
            "-std=c++17",
            optimization,
            "-shared",
            "-fPIC",
            f"-I{cxxrtl_include}",
            f"-I{output_dir}",
            "-DCXXRTL_INCLUDE_CAPI_IMPL",
            "-o", str(lib_path),
            str(wrapper_path),
        ]

        if platform.system() == "Darwin":
            compile_cmd.extend(["-undefined", "dynamic_lookup"])

        logger.info(f"Compiling CXXRTL library: {lib_path}")
        logger.debug(f"Compile command: {' '.join(compile_cmd)}")

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"C++ compilation failed: {result.stderr}")

    logger.info(f"Built CXXRTL library: {lib_path}")
    return lib_path


def build_cxxrtl_from_amaranth(
    elaboratable,
    top_module: str,
    output_dir: Union[str, Path],
    amaranth_platform=None,
    extra_sources: Optional[Sequence[Union[str, Path]]] = None,
    **kwargs,
) -> Path:
    """Build CXXRTL from an Amaranth Elaboratable.

    This function generates Verilog from an Amaranth design and compiles it
    to a CXXRTL shared library, optionally combining with extra Verilog/SV sources.

    Args:
        elaboratable: Amaranth Elaboratable to simulate
        top_module: Name for the top module
        output_dir: Directory for build artifacts
        amaranth_platform: Amaranth platform (optional)
        extra_sources: Additional Verilog/SV files to include
        **kwargs: Additional arguments passed to build_cxxrtl()

    Returns:
        Path to the compiled shared library
    """
    from amaranth.back import rtlil  # type: ignore[attr-defined]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate RTLIL from Amaranth
    rtlil_path = output_dir / f"{top_module}.il"
    logger.info(f"Generating RTLIL for {top_module}")

    rtlil_text = rtlil.convert(elaboratable, platform=amaranth_platform)
    rtlil_path.write_text(rtlil_text)

    # Build Yosys commands - read RTLIL first, then extra sources
    sources: list[Path] = [rtlil_path]
    if extra_sources:
        sources.extend(Path(s) for s in extra_sources)

    # For RTLIL, we need special handling in Yosys
    yosys_cmds = [f"read_rtlil {rtlil_path}"]

    for source in extra_sources or []:
        source = Path(source)
        if source.suffix == ".sv":
            yosys_cmds.append(f"read_slang {source}")
        elif source.suffix == ".il":
            yosys_cmds.append(f"read_rtlil {source}")
        else:
            yosys_cmds.append(f"read_verilog {source}")

    # Elaborate and write CXXRTL
    output_name = kwargs.pop("output_name", top_module)
    lib_ext = _get_shared_lib_extension()
    lib_path = output_dir / f"{output_name}{lib_ext}"
    cc_path = output_dir / f"{output_name}_cxxrtl.cc"

    debug_info = kwargs.pop("debug_info", True)
    cxxrtl_opts = ["-g3"] if debug_info else []

    yosys_cmds.append(f"hierarchy -top {top_module}")
    yosys_cmds.append(f"write_cxxrtl {' '.join(cxxrtl_opts)} {cc_path}")

    # Run Yosys
    logger.info(f"Generating CXXRTL for {top_module}")
    _run_yosys("\n".join(yosys_cmds))

    if not cc_path.exists():
        raise RuntimeError(f"CXXRTL generation failed - {cc_path} not created")

    # Find CXXRTL headers and compile
    cxxrtl_include = _get_cxxrtl_include_path()
    optimization = kwargs.pop("optimization", "-O2")

    # Compile to shared library
    # On macOS: use zig for compilation (consistent builds), system linker for linking
    # On Linux: use system compiler directly (zig uses libc++ which isn't always available)
    zig_cxx = _find_zig_cxx() if platform.system() == "Darwin" else None
    obj_path = output_dir / f"{output_name}_cxxrtl.o"

    if zig_cxx:
        # macOS: Compile to object file with zig, link with system linker
        compile_cmd = [
            *zig_cxx,
            "-std=c++17",
            optimization,
            "-fPIC",
            "-c",
            f"-I{cxxrtl_include}",
            "-DCXXRTL_INCLUDE_CAPI_IMPL",
            "-o", str(obj_path),
            str(cc_path),
        ]

        logger.info(f"Compiling CXXRTL with zig: {obj_path}")
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"C++ compilation failed: {result.stderr}")

        # Link with system linker
        linker = _find_system_linker()
        link_cmd = [
            *linker,
            "-shared",
            "-o", str(lib_path),
            str(obj_path),
            "-undefined", "dynamic_lookup",
        ]

        logger.info(f"Linking CXXRTL library: {lib_path}")
        result = subprocess.run(link_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Linking failed: {result.stderr}")
    else:
        # Fall back to system compiler for everything
        linker = _find_system_linker()
        compile_cmd = [
            *linker,
            "-std=c++17",
            optimization,
            "-shared",
            "-fPIC",
            f"-I{cxxrtl_include}",
            "-DCXXRTL_INCLUDE_CAPI_IMPL",
            "-o", str(lib_path),
            str(cc_path),
        ]

        if platform.system() == "Darwin":
            compile_cmd.extend(["-undefined", "dynamic_lookup"])

        logger.info(f"Compiling CXXRTL library: {lib_path}")
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"C++ compilation failed: {result.stderr}")

    logger.info(f"Built CXXRTL library: {lib_path}")
    return lib_path
