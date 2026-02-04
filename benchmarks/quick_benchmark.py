#!/usr/bin/env python3
"""
Quick Benchmark: RustyAML vs PyYAML

A simplified benchmark script for quick performance comparisons.
Run with: python benchmarks/quick_benchmark.py
"""

import gc
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import rustyyaml
except ImportError:
    print("ERROR: rustyyaml not installed. Run 'maturin develop' first.")
    sys.exit(1)

try:
    import yaml as pyyaml
    try:
        from yaml import CSafeLoader
        HAS_C_EXT = True
    except ImportError:
        HAS_C_EXT = False
    HAS_PYYAML = True
except ImportError:
    HAS_PYYAML = False
    HAS_C_EXT = False


def benchmark(func, iterations=1000):
    """Run a function multiple times and return stats."""
    gc.collect()
    gc.disable()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)

    gc.enable()

    total = sum(times)
    mean = total / len(times)
    return {
        "mean": mean,
        "total": total,
        "min": min(times),
        "max": max(times),
        "iterations": iterations,
        "ops_per_sec": 1.0 / mean if mean > 0 else 0,
    }


def format_time(seconds):
    """Format time in human-readable units."""
    if seconds >= 1:
        return f"{seconds:.3f}s"
    elif seconds >= 0.001:
        return f"{seconds * 1000:.3f}ms"
    else:
        return f"{seconds * 1_000_000:.3f}μs"


def run_comparison(name, yaml_content, iterations=1000):
    """Run a comparison between RustyAML and PyYAML."""
    print(f"\n{'='*60}")
    print(f"Benchmark: {name}")
    print(f"Size: {len(yaml_content):,} bytes, {yaml_content.count(chr(10)):,} lines")
    print(f"Iterations: {iterations:,}")
    print(f"{'='*60}")

    # RustyAML
    rusty = benchmark(lambda: rustyyaml.safe_load(yaml_content), iterations)
    print(f"\n  RustyAML:")
    print(f"    Mean: {format_time(rusty['mean'])}")
    print(f"    Ops/sec: {rusty['ops_per_sec']:,.0f}")

    # PyYAML Pure Python
    if HAS_PYYAML:
        pyyaml_pure = benchmark(lambda: pyyaml.safe_load(yaml_content), iterations)
        speedup = pyyaml_pure['mean'] / rusty['mean']
        print(f"\n  PyYAML (Pure Python):")
        print(f"    Mean: {format_time(pyyaml_pure['mean'])}")
        print(f"    Ops/sec: {pyyaml_pure['ops_per_sec']:,.0f}")
        print(f"    → RustyAML is {speedup:.2f}x faster")

    # PyYAML C Extension
    if HAS_C_EXT:
        pyyaml_c = benchmark(
            lambda: pyyaml.load(yaml_content, Loader=CSafeLoader),
            iterations
        )
        speedup_c = pyyaml_c['mean'] / rusty['mean']
        print(f"\n  PyYAML (C Extension):")
        print(f"    Mean: {format_time(pyyaml_c['mean'])}")
        print(f"    Ops/sec: {pyyaml_c['ops_per_sec']:,.0f}")
        print(f"    → RustyAML is {speedup_c:.2f}x faster")


def main():
    print("=" * 60)
    print("Quick Benchmark: RustyAML vs PyYAML")
    print("=" * 60)
    print(f"PyYAML: {'Yes' if HAS_PYYAML else 'No'}")
    print(f"PyYAML C Extension: {'Yes' if HAS_C_EXT else 'No'}")

    # Test 1: Minimal
    run_comparison(
        "Minimal Config",
        "key: value",
        iterations=5000
    )

    # Test 2: Small config
    small = """
app:
  name: myapp
  version: "1.0.0"
server:
  host: localhost
  port: 8080
database:
  url: postgres://localhost/db
  pool_size: 10
logging:
  level: info
  format: json
"""
    run_comparison("Small Config (~15 lines)", small, iterations=3000)

    # Test 3: Medium config
    medium_lines = ["config:"]
    for i in range(100):
        medium_lines.append(f"  key_{i}: value_{i}")
        medium_lines.append(f"  nested_{i}:")
        medium_lines.append(f"    a: {i}")
        medium_lines.append(f"    b: {i * 2}")
    medium = "\n".join(medium_lines)
    run_comparison("Medium Config (~400 lines)", medium, iterations=1000)

    # Test 4: Large config
    large_lines = ["items:"]
    for i in range(500):
        large_lines.append(f"  - id: {i}")
        large_lines.append(f"    name: item_{i}")
        large_lines.append(f"    value: {i * 100}")
        large_lines.append(f"    enabled: {str(i % 2 == 0).lower()}")
    large = "\n".join(large_lines)
    run_comparison("Large Config (~2000 lines)", large, iterations=200)

    # Test 5: XL config
    xl_lines = []
    for section in range(50):
        xl_lines.append(f"section_{section}:")
        xl_lines.append(f"  name: Section {section}")
        for item in range(50):
            xl_lines.append(f"  item_{item}:")
            xl_lines.append(f"    id: {section}_{item}")
            xl_lines.append(f"    value: {item * section}")
    xl = "\n".join(xl_lines)
    run_comparison("XL Config (~5000+ lines)", xl, iterations=50)

    # Test 6: Batch loading
    print(f"\n{'='*60}")
    print("Benchmark: Batch Loading (100 documents)")
    print(f"{'='*60}")

    docs = [f"doc: {i}\nvalue: {i * 10}" for i in range(100)]

    gc.collect()

    # RustyAML batch
    start = time.perf_counter()
    for _ in range(50):
        rustyyaml.safe_load_many(docs)
    rusty_time = (time.perf_counter() - start) / 50

    print(f"\n  RustyAML (parallel): {format_time(rusty_time)}")

    if HAS_PYYAML:
        start = time.perf_counter()
        for _ in range(50):
            [pyyaml.safe_load(d) for d in docs]
        pyyaml_time = (time.perf_counter() - start) / 50
        print(f"  PyYAML (sequential): {format_time(pyyaml_time)}")
        print(f"  → RustyAML is {pyyaml_time / rusty_time:.2f}x faster")

    print(f"\n{'='*60}")
    print("Benchmark Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
