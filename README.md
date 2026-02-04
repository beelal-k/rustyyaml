# RustyYAML 🦀

**Fast, safe YAML parser for Python** – A drop-in replacement for PyYAML with 10-100x performance improvement.

[![PyPI version](https://badge.fury.io/py/rustyyaml.svg)](https://pypi.org/project/rustyyaml/)
[![CI](https://github.com/beelal-k/rustyyaml/workflows/CI/badge.svg)](https://github.com/beelal-k/rustyyaml/actions)
[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-blue.svg)](LICENSE)

## Features

- ⚡ **10-100x faster** than pure Python PyYAML
- 🔒 **100% safe by default** – No code execution vulnerabilities
- 🎯 **Drop-in replacement** – Compatible with PyYAML API
- 🚀 **Always fast** – No C extension installation required
- 🧵 **Parallel loading** – Parse multiple files simultaneously
- 🐍 **Pure Python API** – Pythonic and easy to use

## Installation

```bash
pip install rustyyaml
```

That's it! No C compiler, no build tools needed.

## Quick Start

```python
import rustyyaml as yaml

# Parse YAML string
data = yaml.safe_load("key: value")
print(data)  # {'key': 'value'}

# Load from file
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Load from Path
from pathlib import Path
config = yaml.safe_load(Path('config.yaml'))

# Parse multiple documents
docs = yaml.load_all("""
doc: 1
---
doc: 2
---
doc: 3
""")
print(len(docs))  # 3

# Batch loading (parallel) - 5-10x faster for multiple files
results = yaml.safe_load_many([yaml1, yaml2, yaml3])

# Load entire directory
configs = yaml.load_directory('./configs', recursive=True)
for filename, data in configs:
    print(f"{filename}: {data}")
```

## Migration from PyYAML

### Option 1: Replace import

```python
# Before
import yaml

# After
import rustyyaml as yaml

# Rest of your code works unchanged!
data = yaml.safe_load("key: value")
```

### Option 2: Use compatibility layer

```python
# Add this line at the top of your main file
import rustyyaml.compat

# All existing code works unchanged
import yaml
config = yaml.safe_load(open('config.yaml'))
```

## Benchmarks

Tested on Apple M2, Python 3.11, parsing a Kubernetes manifest 5000 times:

| Library | Time | Speedup |
|---------|------|---------|
| PyYAML (pure Python) | 12.3s | 1x (baseline) |
| PyYAML (with LibYAML) | 1.8s | 6.8x |
| **RustyYAML** | **0.4s** | **30x** |

### Batch Loading Performance

| Operation | Sequential | Parallel | Speedup |
|-----------|------------|----------|---------|
| 100 files | 0.8s | 0.2s | 4x |
| 1000 files | 8.2s | 1.1s | 7.5x |

## Why RustyYAML?

### The Problem

PyYAML is slow because:
1. It's written in pure Python (interpreted, not compiled)
2. It loops through every element sequentially
3. It creates intermediate Python objects during parsing
4. The C extension (LibYAML) is often missing or hard to install

### The Solution

RustyYAML:
1. Written in Rust (compiled to native code)
2. Uses parallel processing for batch operations
3. Zero-copy parsing where possible
4. Always includes the fast parser (no C extension needed)
5. Pre-built wheels for all major platforms

## Safety

Unlike PyYAML, RustyYAML is **secure by default**:

```python
# This would execute code in PyYAML's unsafe mode
dangerous = "!!python/object/apply:os.system ['rm -rf /']"

# RustyYAML blocks it by default
yaml.safe_load(dangerous)  # Raises YAMLError: Unsafe tag detected

# Only use unsafe_load() if you completely trust the source
yaml.unsafe_load(trusted_yaml)  # Use with caution!
```

## API Reference

### Core Functions

| Function | Description |
|----------|-------------|
| `safe_load(stream)` | Parse YAML safely (recommended) |
| `unsafe_load(stream)` | Parse without safety checks |
| `load(stream)` | Alias for `safe_load()` |
| `load_all(stream)` | Parse multiple documents |

### File Operations

| Function | Description |
|----------|-------------|
| `safe_load_file(path)` | Load YAML from file path |
| `load_all_file(path)` | Load multiple documents from file |

### Batch Operations

| Function | Description |
|----------|-------------|
| `safe_load_many(yamls)` | Parse list of YAML strings in parallel |
| `unsafe_load_many(yamls)` | Parallel parsing without safety checks |
| `load_directory(path, recursive=False)` | Load all YAML files from directory |

### Input Types

All loading functions accept:
- `str` - YAML content as string
- `bytes` - YAML content as bytes (UTF-8)
- `Path` - Path to YAML file
- File objects - Open file handles

## Compatibility

### ✅ Fully Supported

- `yaml.safe_load()` - Drop-in replacement
- `yaml.load()` - Defaults to safe mode (unlike PyYAML!)
- `yaml.load_all()` - Multiple document support
- `yaml.YAMLError` - Exception handling

### ⚠️ Not Yet Supported

- `yaml.dump()` / `yaml.safe_dump()` - Coming in v2.0
- `yaml.YAMLObject` - Custom object serialization
- Custom constructors/representers

## Error Handling

```python
from rustyyaml import YAMLError

try:
    data = yaml.safe_load(invalid_yaml)
except YAMLError as e:
    print(f"Parse error: {e}")
```

## Development

### Building from source

```bash
# Clone the repository
git clone https://github.com/yourusername/rustyaml
cd rustyaml

# Install development dependencies
pip install maturin pytest

# Build and install in development mode
maturin develop

# Run tests
pytest tests/ -v

# Run Rust tests
cargo test

# Run benchmarks
cargo bench
```

### Project Structure

```
rustyaml/
├── Cargo.toml              # Rust dependencies
├── pyproject.toml          # Python packaging
├── src/                    # Rust source code
│   ├── lib.rs              # PyO3 module entry point
│   ├── parser.rs           # YAML parsing logic
│   ├── types.rs            # Type conversion
│   ├── error.rs            # Error handling
│   ├── safe.rs             # Safety filters
│   └── batch.rs            # Parallel batch loading
├── python/rustyaml/        # Python wrapper
│   ├── __init__.py         # Public API
│   └── compat.py           # PyYAML compatibility
├── tests/                  # Test suites
└── benches/                # Criterion benchmarks
```

## Contributing

Contributions welcome! Please read our contributing guidelines before submitting a PR.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Licensed under either of:

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

## Acknowledgments

- Built with [PyO3](https://github.com/PyO3/pyo3) - Rust bindings for Python
- Uses [serde_yaml](https://github.com/dtolnay/serde-yaml) - Rust YAML parser
- Inspired by [orjson](https://github.com/ijl/orjson) and [polars](https://github.com/pola-rs/polars)

## Changelog

### v0.1.0

- Initial release
- Core YAML parsing functionality
- PyYAML API compatibility
- Parallel batch loading
- Safety filters for dangerous tags