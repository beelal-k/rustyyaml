# RustyAML Benchmarks

This directory contains comprehensive benchmarks comparing RustyAML against PyYAML.

## Quick Start

First, make sure RustyAML is built and installed:

```bash
# From the rustyaml directory
python -m venv .venv
source .venv/bin/activate
pip install maturin pyyaml
maturin develop --release
```

Then run the benchmarks:

```bash
# Quick benchmark (recommended for first run)
python benchmarks/quick_benchmark.py

# Full benchmark suite
python benchmarks/benchmark_comparison.py

# Full benchmark with JSON export
python benchmarks/benchmark_comparison.py --json results.json

# Quick mode (faster, less iterations)
python benchmarks/benchmark_comparison.py --quick

# Verbose output (detailed stats per benchmark)
python benchmarks/benchmark_comparison.py -v
```

## Benchmark Scripts

### `quick_benchmark.py`

A simple, fast benchmark for everyday performance testing. Tests:
- Minimal config (1 key)
- Small config (~15 lines)
- Medium config (~400 lines)
- Large config (~2000 lines)
- XL config (~5000+ lines)
- Batch loading (100 documents)

### `benchmark_comparison.py`

Comprehensive benchmark suite with:
- Multiple configuration sizes (small → production-scale)
- Generated test data with various structures
- Batch/parallel processing tests
- Multi-document YAML stream tests
- Statistical analysis (mean, median, stddev, min, max)
- JSON export for further analysis

## Test Fixtures

The benchmarks use fixtures from `tests/fixtures/`:

| File | Size | Description |
|------|------|-------------|
| `small_config.yaml` | ~20 lines | Simple app configuration |
| `medium_config.yaml` | ~200 lines | Microservices configuration |
| `large_config.yaml` | ~1200 lines | Kubernetes cluster config |
| `kubernetes.yaml` | ~130 lines | Multi-document K8s manifest |

Additionally, the full benchmark generates:
- Flat configs (50 → 10,000 keys)
- Nested configs (configurable depth/breadth)
- List configs (100 → 2,000 items)
- Enterprise configs (~5000+ lines)
- Multi-document streams (10 → 100 documents)

## Sample Results

Results vary by hardware. Here's what to expect on a modern system:

| Benchmark | RustyAML | PyYAML | PyYAML-C | Speedup vs C |
|-----------|----------|--------|----------|--------------|
| Minimal (1 key) | ~5μs | ~50μs | ~15μs | ~3x |
| Small config | ~15μs | ~150μs | ~40μs | ~2.5x |
| Medium config | ~100μs | ~1ms | ~250μs | ~2.5x |
| Large config | ~500μs | ~5ms | ~1.5ms | ~3x |
| XL config | ~2ms | ~25ms | ~8ms | ~4x |
| Batch (100 docs) | ~200μs | ~5ms | ~1.5ms | ~7x* |

\* Batch operations use parallel processing, providing additional speedup on multi-core systems.

## Comparison Notes

### Libraries Tested

- **RustyAML**: Rust-based YAML parser with PyO3 bindings
- **PyYAML (Pure Python)**: `yaml.safe_load()` with default loader
- **PyYAML (C Extension)**: `yaml.load(Loader=CSafeLoader)` with libyaml

### What's Measured

- **Parsing time only**: Time to parse YAML string → Python objects
- **Cold start excluded**: Warmup iterations run before measurement
- **GC disabled**: Garbage collection disabled during timing
- **Per-iteration timing**: Individual times recorded for statistics

### Factors Affecting Performance

1. **YAML complexity**: Deeply nested structures are slower
2. **String content**: Many unique strings reduce interning benefits
3. **List sizes**: Large lists have more Python object overhead
4. **CPU cores**: Batch operations scale with available cores

## Extending the Benchmarks

Add custom benchmarks by using the helper functions:

```python
from benchmark_comparison import benchmark_yaml_string, print_comparison

# Your custom YAML
my_yaml = """
custom:
  config:
    here: true
"""

result = benchmark_yaml_string(
    name="My Custom Benchmark",
    yaml_string=my_yaml,
    description="Testing custom config"
)

print_comparison(result)
```

## CI Integration

Run benchmarks in CI with quick mode and JSON export:

```bash
python benchmarks/benchmark_comparison.py --quick --json benchmark_results.json
```

The JSON output can be compared across commits to detect performance regressions.