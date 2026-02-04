"""
PyYAML compatibility layer

Import this module to replace PyYAML with RustyAML globally:

    import rustyaml.compat  # Must be first import
    import yaml  # This is now RustyAML!

This allows zero-code migration from PyYAML to RustyAML.
"""

import sys
import warnings
from typing import Any

# Import RustyAML
from . import (
    YAMLError,
    __version__,
    load,
    load_all,
    safe_load,
    unsafe_load,
)


# PyYAML compatibility aliases
class YAMLObject:
    """Stub for PyYAML's YAMLObject (not supported in v1)"""

    yaml_tag = None
    yaml_loader = None
    yaml_dumper = None

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "YAMLObject is not supported in RustyAML v1. "
            "Use safe_load() with plain Python objects instead."
        )

    @classmethod
    def from_yaml(cls, loader, node):
        raise NotImplementedError("YAMLObject.from_yaml() is not supported")

    @classmethod
    def to_yaml(cls, dumper, data):
        raise NotImplementedError("YAMLObject.to_yaml() is not supported")


class Loader:
    """Stub for PyYAML's Loader"""
    pass


class SafeLoader:
    """Stub for PyYAML's SafeLoader"""
    pass


class FullLoader:
    """Stub for PyYAML's FullLoader"""
    pass


class UnsafeLoader:
    """Stub for PyYAML's UnsafeLoader"""
    pass


class Dumper:
    """Stub for PyYAML's Dumper"""
    pass


class SafeDumper:
    """Stub for PyYAML's SafeDumper"""
    pass


class BaseLoader:
    """Stub for PyYAML's BaseLoader"""
    pass


class BaseDumper:
    """Stub for PyYAML's BaseDumper"""
    pass


# Functions not yet implemented
def dump(*args, **kwargs) -> str:
    """Dump Python object to YAML (not implemented in v1)"""
    raise NotImplementedError(
        "dump() is not yet implemented in RustyAML v1. "
        "Use PyYAML for YAML generation, or wait for RustyAML v2."
    )


def dump_all(*args, **kwargs) -> str:
    """Dump multiple documents to YAML (not implemented in v1)"""
    raise NotImplementedError("dump_all() not yet implemented")


def safe_dump(*args, **kwargs) -> str:
    """Safe dump to YAML (not implemented in v1)"""
    raise NotImplementedError("safe_dump() not yet implemented")


def safe_dump_all(*args, **kwargs) -> str:
    """Safe dump multiple documents (not implemented in v1)"""
    raise NotImplementedError("safe_dump_all() not yet implemented")


def add_constructor(tag, constructor, Loader=None):
    """Add a constructor (not implemented)"""
    raise NotImplementedError(
        "add_constructor() is not supported in RustyAML. "
        "Custom constructors are a security risk."
    )


def add_representer(data_type, representer, Dumper=None):
    """Add a representer (not implemented)"""
    raise NotImplementedError("add_representer() not yet implemented")


def add_implicit_resolver(tag, regexp, first, Loader=None, Dumper=None):
    """Add implicit resolver (not implemented)"""
    raise NotImplementedError("add_implicit_resolver() not yet implemented")


def add_path_resolver(tag, path, kind=None, Loader=None, Dumper=None):
    """Add path resolver (not implemented)"""
    raise NotImplementedError("add_path_resolver() not yet implemented")


def add_multi_constructor(tag_prefix, multi_constructor, Loader=None):
    """Add multi-constructor (not implemented)"""
    raise NotImplementedError("add_multi_constructor() not yet implemented")


def add_multi_representer(data_type, multi_representer, Dumper=None):
    """Add multi-representer (not implemented)"""
    raise NotImplementedError("add_multi_representer() not yet implemented")


def compose(stream, Loader=None):
    """Compose a YAML document (not implemented)"""
    raise NotImplementedError("compose() not yet implemented")


def compose_all(stream, Loader=None):
    """Compose all YAML documents (not implemented)"""
    raise NotImplementedError("compose_all() not yet implemented")


def emit(events, stream=None, Dumper=None, **kwargs):
    """Emit YAML events (not implemented)"""
    raise NotImplementedError("emit() not yet implemented")


def serialize(node, stream=None, Dumper=None, **kwargs):
    """Serialize a node (not implemented)"""
    raise NotImplementedError("serialize() not yet implemented")


def serialize_all(nodes, stream=None, Dumper=None, **kwargs):
    """Serialize all nodes (not implemented)"""
    raise NotImplementedError("serialize_all() not yet implemented")


def scan(stream, Loader=None):
    """Scan YAML tokens (not implemented)"""
    raise NotImplementedError("scan() not yet implemented")


def parse(stream, Loader=None):
    """Parse YAML events (not implemented)"""
    raise NotImplementedError("parse() not yet implemented")


# Create a fake 'yaml' module
class YAMLModule:
    """
    Fake 'yaml' module that uses RustyAML under the hood

    This allows code that does:
        import yaml
        data = yaml.safe_load(file)

    To automatically use RustyAML instead.
    """

    # Core loading functions
    safe_load = staticmethod(safe_load)
    unsafe_load = staticmethod(unsafe_load)
    load = staticmethod(load)
    load_all = staticmethod(load_all)

    # Dump functions (not implemented)
    dump = staticmethod(dump)
    dump_all = staticmethod(dump_all)
    safe_dump = staticmethod(safe_dump)
    safe_dump_all = staticmethod(safe_dump_all)

    # Constructor/representer functions (not implemented)
    add_constructor = staticmethod(add_constructor)
    add_representer = staticmethod(add_representer)
    add_implicit_resolver = staticmethod(add_implicit_resolver)
    add_path_resolver = staticmethod(add_path_resolver)
    add_multi_constructor = staticmethod(add_multi_constructor)
    add_multi_representer = staticmethod(add_multi_representer)

    # Low-level functions (not implemented)
    compose = staticmethod(compose)
    compose_all = staticmethod(compose_all)
    emit = staticmethod(emit)
    serialize = staticmethod(serialize)
    serialize_all = staticmethod(serialize_all)
    scan = staticmethod(scan)
    parse = staticmethod(parse)

    # Classes
    YAMLObject = YAMLObject
    YAMLError = YAMLError
    Loader = Loader
    SafeLoader = SafeLoader
    FullLoader = FullLoader
    UnsafeLoader = UnsafeLoader
    Dumper = Dumper
    SafeDumper = SafeDumper
    BaseLoader = BaseLoader
    BaseDumper = BaseDumper

    # Metadata
    __version__ = __version__
    __name__ = "yaml"
    __file__ = __file__
    __doc__ = "PyYAML compatibility layer powered by RustyAML"

    # Mark as RustyAML for detection
    __rustyaml__ = True
    __rustyaml_version__ = __version__


# Replace 'yaml' in sys.modules
_yaml_module = YAMLModule()
sys.modules["yaml"] = _yaml_module  # type: ignore

# Warn the user
warnings.warn(
    "PyYAML has been replaced with RustyAML via rustyaml.compat. "
    "Some PyYAML features (dump, YAMLObject) are not yet supported.",
    UserWarning,
    stacklevel=2,
)
