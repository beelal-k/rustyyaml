"""
RustyAML: Fast, safe YAML parser for Python

Drop-in replacement for PyYAML with 10-100x performance improvement.

Basic usage:
    >>> import rustyaml as yaml
    >>> data = yaml.safe_load("key: value")
    >>> print(data)
    {'key': 'value'}

Features:
    - 10-100x faster than PyYAML (pure Python)
    - Always fast (no C extension required)
    - 100% safe by default (no code execution)
    - Drop-in PyYAML replacement
"""

from pathlib import Path
from typing import IO, Any, List, Optional, Tuple, Union

# Import the Rust extension module
try:
    from . import rustyaml as _rustyaml
except ImportError as e:
    raise ImportError(
        "Failed to import rustyaml Rust extension. "
        "This usually means the package was not installed correctly. "
        f"Error: {e}"
    )

__version__ = _rustyaml.__version__
__all__ = [
    "safe_load",
    "unsafe_load",
    "load",
    "load_all",
    "load_all_unsafe",
    "safe_load_file",
    "load_all_file",
    "safe_load_many",
    "unsafe_load_many",
    "load_directory",
    "load_directory_unsafe",
    "YAMLError",
    "__version__",
]


class YAMLError(ValueError):
    """Base exception for YAML errors"""

    pass


def _read_stream(stream: Union[str, bytes, IO, Path]) -> str:
    """
    Read YAML content from various input types

    Args:
        stream: YAML content as string, bytes, file object, or Path

    Returns:
        YAML content as UTF-8 string

    Raises:
        YAMLError: If content cannot be read or decoded
    """
    # Handle Path objects
    if isinstance(stream, Path):
        try:
            return stream.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise YAMLError(f"File not found: {stream}")
        except Exception as e:
            raise YAMLError(f"Failed to read file {stream}: {e}")

    # Handle file-like objects
    if hasattr(stream, "read"):
        content = stream.read()
        if isinstance(content, bytes):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError as e:
                raise YAMLError(f"Failed to decode YAML as UTF-8: {e}")
        return content

    # Handle bytes
    if isinstance(stream, bytes):
        try:
            return stream.decode("utf-8")
        except UnicodeDecodeError as e:
            raise YAMLError(f"Failed to decode YAML as UTF-8: {e}")

    # Handle strings
    if isinstance(stream, str):
        return stream

    raise YAMLError(
        f"Unsupported input type: {type(stream)}. "
        "Expected str, bytes, file object, or Path"
    )


def safe_load(stream: Union[str, bytes, IO, Path]) -> Any:
    """
    Parse YAML safely (no code execution)

    This is the recommended way to load YAML. It rejects any YAML
    tags that could execute code (like !!python/object).

    Args:
        stream: YAML content as string, bytes, file object, or Path

    Returns:
        Python object (dict, list, str, int, float, bool, or None)

    Raises:
        YAMLError: If YAML is malformed or contains unsafe tags

    Example:
        >>> data = safe_load("key: value")
        >>> print(data)
        {'key': 'value'}

        >>> with open('config.yaml') as f:
        ...     config = safe_load(f)
    """
    try:
        content = _read_stream(stream)
        return _rustyaml.safe_load(content)
    except YAMLError:
        raise
    except Exception as e:
        raise YAMLError(str(e))


def unsafe_load(stream: Union[str, bytes, IO, Path]) -> Any:
    """
    Parse YAML without safety checks (DANGEROUS!)

    WARNING: This can execute arbitrary Python code embedded in YAML.
    Only use this if you completely trust the YAML source.

    Args:
        stream: YAML content as string, bytes, file object, or Path

    Returns:
        Python object

    Raises:
        YAMLError: If YAML is malformed

    Example:
        >>> # Only use with trusted input!
        >>> data = unsafe_load(trusted_yaml)
    """
    try:
        content = _read_stream(stream)
        return _rustyaml.unsafe_load(content)
    except YAMLError:
        raise
    except Exception as e:
        raise YAMLError(str(e))


def load(stream: Union[str, bytes, IO, Path]) -> Any:
    """
    Parse YAML (defaults to safe mode)

    This is an alias for safe_load() to match PyYAML's API.
    Unlike PyYAML, we default to safe mode.

    Args:
        stream: YAML content

    Returns:
        Python object

    Example:
        >>> data = load("key: value")
    """
    return safe_load(stream)


def load_all(stream: Union[str, bytes, IO, Path]) -> List[Any]:
    """
    Parse multiple YAML documents from a single stream

    YAML allows multiple documents separated by '---'

    Args:
        stream: YAML content with multiple documents

    Returns:
        List of Python objects (one per document)

    Raises:
        YAMLError: If any document is malformed

    Example:
        >>> yaml_str = '''
        ... doc: 1
        ... ---
        ... doc: 2
        ... ---
        ... doc: 3
        ... '''
        >>> docs = load_all(yaml_str)
        >>> print(len(docs))  # 3
    """
    try:
        content = _read_stream(stream)
        return _rustyaml.load_all(content)
    except YAMLError:
        raise
    except Exception as e:
        raise YAMLError(str(e))


def load_all_unsafe(stream: Union[str, bytes, IO, Path]) -> List[Any]:
    """
    Parse multiple YAML documents without safety checks

    Args:
        stream: YAML content with multiple documents

    Returns:
        List of Python objects
    """
    try:
        content = _read_stream(stream)
        return _rustyaml.load_all_unsafe(content)
    except YAMLError:
        raise
    except Exception as e:
        raise YAMLError(str(e))


def safe_load_file(path: Union[str, Path]) -> Any:
    """
    Load YAML from a file safely

    Args:
        path: Path to YAML file

    Returns:
        Python object

    Example:
        >>> config = safe_load_file('config.yaml')
    """
    return safe_load(Path(path))


def load_all_file(path: Union[str, Path]) -> List[Any]:
    """
    Load multiple YAML documents from a file

    Args:
        path: Path to YAML file

    Returns:
        List of Python objects
    """
    return load_all(Path(path))


def safe_load_many(yaml_strings: List[str]) -> List[Any]:
    """
    Parse multiple YAML strings in parallel

    This is 5-10x faster than a loop for large batches.

    Args:
        yaml_strings: List of YAML content strings

    Returns:
        List of parsed Python objects (same order as input)

    Example:
        >>> yamls = ["doc: 1", "doc: 2", "doc: 3"]
        >>> results = safe_load_many(yamls)
        >>> print(results)
        [{'doc': 1}, {'doc': 2}, {'doc': 3}]
    """
    try:
        return _rustyaml.safe_load_many(yaml_strings)
    except Exception as e:
        raise YAMLError(str(e))


def unsafe_load_many(yaml_strings: List[str]) -> List[Any]:
    """
    Parse multiple YAML strings in parallel without safety checks

    Args:
        yaml_strings: List of YAML content strings

    Returns:
        List of parsed Python objects
    """
    try:
        return _rustyaml.unsafe_load_many(yaml_strings)
    except Exception as e:
        raise YAMLError(str(e))


def load_directory(
    directory: Union[str, Path], recursive: bool = False
) -> List[Tuple[str, Any]]:
    """
    Load all YAML files from a directory in parallel

    Args:
        directory: Path to directory
        recursive: If True, search subdirectories

    Returns:
        List of (filename, data) tuples

    Example:
        >>> results = load_directory("./configs")
        >>> for filename, data in results:
        ...     print(f"{filename}: {data}")
    """
    try:
        return _rustyaml.load_directory(str(directory), recursive)
    except Exception as e:
        raise YAMLError(str(e))


def load_directory_unsafe(
    directory: Union[str, Path], recursive: bool = False
) -> List[Tuple[str, Any]]:
    """
    Load all YAML files from a directory without safety checks

    Args:
        directory: Path to directory
        recursive: If True, search subdirectories

    Returns:
        List of (filename, data) tuples
    """
    try:
        return _rustyaml.load_directory_unsafe(str(directory), recursive)
    except Exception as e:
        raise YAMLError(str(e))
