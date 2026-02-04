"""Type stubs for RustyYAML"""

from pathlib import Path
from typing import IO, Any, List, Tuple, Union

StreamType = Union[str, bytes, IO[str], IO[bytes], Path]

class YAMLError(ValueError):
    """Base exception for YAML errors"""
    ...

def safe_load(stream: StreamType) -> Any:
    """Parse YAML safely (no code execution)"""
    ...

def unsafe_load(stream: StreamType) -> Any:
    """Parse YAML without safety checks (DANGEROUS!)"""
    ...

def load(stream: StreamType) -> Any:
    """Parse YAML (defaults to safe mode)"""
    ...

def load_all(stream: StreamType) -> List[Any]:
    """Parse multiple YAML documents from a single stream"""
    ...

def load_all_unsafe(stream: StreamType) -> List[Any]:
    """Parse multiple YAML documents without safety checks"""
    ...

def safe_load_file(path: Union[str, Path]) -> Any:
    """Load YAML from a file safely"""
    ...

def load_all_file(path: Union[str, Path]) -> List[Any]:
    """Load multiple YAML documents from a file"""
    ...

def safe_load_many(yaml_strings: List[str]) -> List[Any]:
    """Parse multiple YAML strings in parallel"""
    ...

def unsafe_load_many(yaml_strings: List[str]) -> List[Any]:
    """Parse multiple YAML strings in parallel without safety checks"""
    ...

def load_directory(
    directory: Union[str, Path], recursive: bool = False
) -> List[Tuple[str, Any]]:
    """Load all YAML files from a directory in parallel"""
    ...

def load_directory_unsafe(
    directory: Union[str, Path], recursive: bool = False
) -> List[Tuple[str, Any]]:
    """Load all YAML files from a directory without safety checks"""
    ...

__version__: str
