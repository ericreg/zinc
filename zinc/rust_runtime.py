"""Helpers for Zinc Rust runtime support files."""

import os
import shutil
from pathlib import Path

RUNTIME_PACKAGE_NAME = "zinc-internal"
RUNTIME_CRATE_NAME = "zinc_internal"
RUNTIME_MODULE_NAME = RUNTIME_PACKAGE_NAME


def runtime_source_dir() -> Path:
    """Return the canonical Zinc Rust runtime source directory."""
    return Path(__file__).resolve().parent.parent / "rust_runtime" / RUNTIME_PACKAGE_NAME


def runtime_module_file(runtime_root: Path) -> Path:
    """Return the path to the runtime crate root file under a target root."""
    return runtime_root / RUNTIME_PACKAGE_NAME / "src" / "lib.rs"


def runtime_module_path_for_output(output_file: Path, runtime_mod_file: Path) -> str:
    """Return a Rust #[path] value from an output file to a runtime module."""
    relative = os.path.relpath(runtime_mod_file, output_file.parent)
    return Path(relative).as_posix()


def sync_runtime(runtime_root: Path) -> Path:
    """Copy the canonical runtime into a target directory."""
    source = runtime_source_dir()
    target = runtime_root / RUNTIME_MODULE_NAME
    shutil.copytree(source, target, dirs_exist_ok=True)
    return target
