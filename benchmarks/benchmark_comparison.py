#!/usr/bin/env python3
"""
Comprehensive Benchmark Suite: RustyAML vs PyYAML

This benchmark compares parsing performance across various YAML sizes:
- Small: Simple app config (~20 lines)
- Medium: Microservices config (~200 lines)
- Large: Kubernetes cluster config (~1000 lines)
- X-Large: Enterprise production config (~5000+ lines, generated)

Run with: python benchmarks/benchmark_comparison.py
"""

import gc
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

# Add the project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import rustyaml
    HAS_RUSTYAML = True
except ImportError:
    HAS_RUSTYAML = False
    print("ERROR: rustyaml not installed. Run 'maturin develop' first.")
    sys.exit(1)

try:
    import yaml as pyyaml
    # Check if we have C extensions
    try:
        from yaml import CSafeLoader
        HAS_PYYAML_C = True
    except ImportError:
        HAS_PYYAML_C = False
    HAS_PYYAML = True
except ImportError:
    HAS_PYYAML = False
    HAS_PYYAML_C = False
    print("WARNING: PyYAML not installed. Install with 'pip install pyyaml'")


# ============================================================================
# Benchmark Configuration
# ============================================================================

WARMUP_ITERATIONS = 5
MIN_ITERATIONS = 10
MAX_ITERATIONS = 10000
TARGET_TIME_SECONDS = 2.0  # Run each benchmark for at least this long

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    name: str
    library: str
    iterations: int
    total_time: float
    times: List[float] = field(default_factory=list)

    @property
    def mean_time(self) -> float:
        return statistics.mean(self.times) if self.times else self.total_time / self.iterations

    @property
    def median_time(self) -> float:
        return statistics.median(self.times) if self.times else self.mean_time

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else self.mean_time

    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else self.mean_time

    @property
    def ops_per_second(self) -> float:
        return 1.0 / self.mean_time if self.mean_time > 0 else 0


@dataclass
class ComparisonResult:
    """Comparison between two benchmark results."""
    benchmark_name: str
    rustyaml_result: BenchmarkResult
    pyyaml_result: Optional[BenchmarkResult]
    pyyaml_c_result: Optional[BenchmarkResult] = None

    @property
    def speedup_vs_pyyaml(self) -> Optional[float]:
        if self.pyyaml_result:
            return self.pyyaml_result.mean_time / self.rustyaml_result.mean_time
        return None

    @property
    def speedup_vs_pyyaml_c(self) -> Optional[float]:
        if self.pyyaml_c_result:
            return self.pyyaml_c_result.mean_time / self.rustyaml_result.mean_time
        return None


# ============================================================================
# YAML Generators
# ============================================================================

def generate_flat_config(num_keys: int) -> str:
    """Generate a flat key-value YAML config."""
    lines = [f"key_{i}: value_{i}" for i in range(num_keys)]
    return "\n".join(lines)


def generate_nested_config(depth: int, breadth: int) -> str:
    """Generate a deeply nested YAML config."""
    def build_level(current_depth: int, prefix: str = "") -> List[str]:
        lines = []
        indent = "  " * current_depth
        for i in range(breadth):
            key = f"{prefix}node_{i}"
            if current_depth < depth:
                lines.append(f"{indent}{key}:")
                lines.extend(build_level(current_depth + 1, f"{key}_"))
            else:
                lines.append(f"{indent}{key}: leaf_value_{i}")
        return lines

    return "\n".join(build_level(0))


def generate_list_config(num_items: int, fields_per_item: int = 5) -> str:
    """Generate a YAML with a large list of objects."""
    lines = ["items:"]
    for i in range(num_items):
        lines.append(f"  - id: {i}")
        lines.append(f"    name: item_{i}")
        lines.append(f"    description: \"This is item number {i} with a description\"")
        lines.append(f"    enabled: {str(i % 2 == 0).lower()}")
        lines.append(f"    priority: {i % 10}")
        for j in range(fields_per_item - 5):
            lines.append(f"    field_{j}: value_{j}_{i}")
    return "\n".join(lines)


def generate_mixed_config(sections: int, items_per_section: int) -> str:
    """Generate a mixed config with various YAML features."""
    lines = ["# Generated mixed configuration", ""]

    for s in range(sections):
        lines.append(f"section_{s}:")
        lines.append(f"  name: Section {s}")
        lines.append(f"  enabled: {str(s % 2 == 0).lower()}")
        lines.append(f"  settings:")
        lines.append(f"    timeout: {100 + s * 10}")
        lines.append(f"    retries: {3 + s}")
        lines.append(f"    endpoints:")
        for e in range(3):
            lines.append(f"      - url: https://api-{s}-{e}.example.com")
            lines.append(f"        weight: {10 + e}")
        lines.append(f"  items:")
        for i in range(items_per_section):
            lines.append(f"    - id: {s}_{i}")
            lines.append(f"      value: {i * s}")
            lines.append(f"      tags:")
            lines.append(f"        - tag_a_{i}")
            lines.append(f"        - tag_b_{i}")
        lines.append(f"  metadata:")
        lines.append(f"    created: 2024-01-{(s % 28) + 1:02d}")
        lines.append(f"    version: \"1.{s}.0\"")
        lines.append(f"    author: developer_{s}")
        lines.append("")

    return "\n".join(lines)


def generate_xlarge_enterprise_config() -> str:
    """
    Generate an extra-large enterprise configuration (~5000+ lines).
    Simulates a complex microservices platform configuration.
    """
    lines = [
        "# Enterprise Platform Configuration",
        "# Auto-generated for benchmarking",
        "",
        "platform:",
        "  name: enterprise-platform",
        "  version: \"5.0.0\"",
        "  environment: production",
        "  region: us-east-1",
        "",
    ]

    # Generate 20 microservices
    lines.append("services:")
    for svc in range(20):
        svc_name = f"service_{svc:02d}"
        lines.append(f"  {svc_name}:")
        lines.append(f"    name: {svc_name}")
        lines.append(f"    version: \"2.{svc}.0\"")
        lines.append(f"    replicas: {3 + svc % 5}")
        lines.append(f"    port: {8000 + svc}")
        lines.append(f"    health_check:")
        lines.append(f"      path: /health")
        lines.append(f"      interval: 30")
        lines.append(f"      timeout: 10")
        lines.append(f"    resources:")
        lines.append(f"      cpu: \"{(svc % 4 + 1) * 250}m\"")
        lines.append(f"      memory: \"{(svc % 4 + 1) * 256}Mi\"")
        lines.append(f"    environment:")
        for env in range(10):
            lines.append(f"      ENV_VAR_{env}: value_{env}_{svc}")
        lines.append(f"    dependencies:")
        for dep in range(min(5, svc)):
            lines.append(f"      - service_{dep:02d}")
        lines.append(f"    endpoints:")
        for ep in range(5):
            lines.append(f"      - path: /api/v{ep + 1}/{svc_name}")
            lines.append(f"        methods:")
            lines.append(f"          - GET")
            lines.append(f"          - POST")
            lines.append(f"        rate_limit: {1000 + ep * 100}")
        lines.append(f"    scaling:")
        lines.append(f"      min_replicas: {1 + svc % 3}")
        lines.append(f"      max_replicas: {10 + svc % 10}")
        lines.append(f"      cpu_threshold: 70")
        lines.append(f"      memory_threshold: 80")
        lines.append("")

    # Database configurations
    lines.append("databases:")
    for db in range(5):
        db_name = f"database_{db:02d}"
        lines.append(f"  {db_name}:")
        lines.append(f"    type: postgresql")
        lines.append(f"    host: db-{db}.internal")
        lines.append(f"    port: 5432")
        lines.append(f"    name: db_{db}")
        lines.append(f"    pool:")
        lines.append(f"      min: {5 + db * 5}")
        lines.append(f"      max: {50 + db * 10}")
        lines.append(f"      idle_timeout: 300")
        lines.append(f"    replicas:")
        for r in range(3):
            lines.append(f"      - host: db-{db}-replica-{r}.internal")
            lines.append(f"        port: 5432")
            lines.append(f"        priority: {r + 1}")
        lines.append("")

    # Cache configurations
    lines.append("caches:")
    for cache in range(3):
        lines.append(f"  redis_{cache:02d}:")
        lines.append(f"    cluster: true")
        lines.append(f"    nodes:")
        for node in range(6):
            lines.append(f"      - host: redis-{cache}-{node}.internal")
            lines.append(f"        port: 6379")
        lines.append(f"    ttl_defaults:")
        lines.append(f"      session: 3600")
        lines.append(f"      token: 86400")
        lines.append(f"      cache: 300")
        lines.append("")

    # Message queues
    lines.append("messaging:")
    lines.append("  rabbitmq:")
    lines.append("    nodes:")
    for node in range(3):
        lines.append(f"      - host: rabbitmq-{node}.internal")
        lines.append(f"        port: 5672")
    lines.append("    exchanges:")
    for ex in range(10):
        lines.append(f"      - name: exchange_{ex}")
        lines.append(f"        type: topic")
        lines.append(f"        durable: true")
    lines.append("    queues:")
    for q in range(20):
        lines.append(f"      - name: queue_{q}")
        lines.append(f"        durable: true")
        lines.append(f"        prefetch: {10 + q}")
        lines.append(f"        bindings:")
        lines.append(f"          - exchange: exchange_{q % 10}")
        lines.append(f"            routing_key: \"events.{q}.*\"")
    lines.append("")

    # Feature flags (100 flags)
    lines.append("feature_flags:")
    for ff in range(100):
        lines.append(f"  feature_{ff:03d}:")
        lines.append(f"    enabled: {str(ff % 3 != 0).lower()}")
        lines.append(f"    rollout_percentage: {(ff * 7) % 100}")
        lines.append(f"    description: \"Feature flag number {ff}\"")
        lines.append(f"    owner: team_{ff % 10}")
        if ff % 5 == 0:
            lines.append(f"    variants:")
            lines.append(f"      - name: control")
            lines.append(f"        weight: 50")
            lines.append(f"      - name: treatment")
            lines.append(f"        weight: 50")
    lines.append("")

    # Monitoring and alerting
    lines.append("monitoring:")
    lines.append("  metrics:")
    lines.append("    enabled: true")
    lines.append("    retention: 30d")
    lines.append("    aggregations:")
    for agg in ["1m", "5m", "1h", "1d"]:
        lines.append(f"      - interval: {agg}")
        lines.append(f"        functions:")
        lines.append(f"          - avg")
        lines.append(f"          - max")
        lines.append(f"          - p50")
        lines.append(f"          - p99")
    lines.append("  alerts:")
    for alert in range(50):
        lines.append(f"    - name: alert_{alert:02d}")
        lines.append(f"      severity: {['info', 'warning', 'critical'][alert % 3]}")
        lines.append(f"      condition: \"metric > {100 + alert * 10}\"")
        lines.append(f"      duration: {60 + alert * 30}s")
        lines.append(f"      channels:")
        lines.append(f"        - slack")
        lines.append(f"        - pagerduty")
    lines.append("")

    # Security rules
    lines.append("security:")
    lines.append("  cors:")
    lines.append("    allowed_origins:")
    for origin in range(20):
        lines.append(f"      - https://app-{origin}.example.com")
    lines.append("  rate_limits:")
    for rl in range(10):
        lines.append(f"    - path: /api/v1/endpoint_{rl}")
        lines.append(f"      requests_per_second: {100 + rl * 50}")
        lines.append(f"      burst: {200 + rl * 100}")
    lines.append("  ip_allowlist:")
    for ip in range(50):
        lines.append(f"    - 10.0.{ip}.0/24")
    lines.append("")

    return "\n".join(lines)


def generate_multi_document_yaml(num_docs: int, lines_per_doc: int = 20) -> str:
    """Generate a multi-document YAML stream."""
    docs = []
    for d in range(num_docs):
        doc_lines = [
            "---",
            f"document: {d}",
            f"metadata:",
            f"  id: doc_{d}",
            f"  version: \"1.0.{d}\"",
            f"data:",
        ]
        for i in range(lines_per_doc - 6):
            doc_lines.append(f"  field_{i}: value_{i}_{d}")
        docs.append("\n".join(doc_lines))
    return "\n".join(docs)


# ============================================================================
# Benchmark Runner
# ============================================================================

def run_benchmark(
    name: str,
    func: Callable[[], None],
    warmup: int = WARMUP_ITERATIONS,
    target_time: float = TARGET_TIME_SECONDS,
    min_iter: int = MIN_ITERATIONS,
    max_iter: int = MAX_ITERATIONS,
) -> BenchmarkResult:
    """Run a benchmark with warmup and adaptive iteration count."""

    # Warmup
    for _ in range(warmup):
        func()

    # Force garbage collection
    gc.collect()
    gc.disable()

    try:
        # Determine iteration count based on target time
        start = time.perf_counter()
        func()
        single_time = time.perf_counter() - start

        if single_time > 0:
            estimated_iterations = int(target_time / single_time)
            iterations = max(min_iter, min(max_iter, estimated_iterations))
        else:
            iterations = max_iter

        # Run benchmark
        times = []
        total_start = time.perf_counter()

        for _ in range(iterations):
            iter_start = time.perf_counter()
            func()
            iter_end = time.perf_counter()
            times.append(iter_end - iter_start)

        total_time = time.perf_counter() - total_start

        return BenchmarkResult(
            name=name,
            library="",
            iterations=iterations,
            total_time=total_time,
            times=times,
        )

    finally:
        gc.enable()


def format_time(seconds: float) -> str:
    """Format time in appropriate units."""
    if seconds >= 1:
        return f"{seconds:.3f}s"
    elif seconds >= 0.001:
        return f"{seconds * 1000:.3f}ms"
    elif seconds >= 0.000001:
        return f"{seconds * 1_000_000:.3f}μs"
    else:
        return f"{seconds * 1_000_000_000:.3f}ns"


def format_ops(ops: float) -> str:
    """Format operations per second."""
    if ops >= 1_000_000:
        return f"{ops / 1_000_000:.2f}M ops/s"
    elif ops >= 1_000:
        return f"{ops / 1_000:.2f}K ops/s"
    else:
        return f"{ops:.2f} ops/s"


def print_result(result: BenchmarkResult, indent: int = 4):
    """Print a single benchmark result."""
    prefix = " " * indent
    print(f"{prefix}Mean:   {format_time(result.mean_time)}")
    print(f"{prefix}Median: {format_time(result.median_time)}")
    print(f"{prefix}Min:    {format_time(result.min_time)}")
    print(f"{prefix}Max:    {format_time(result.max_time)}")
    print(f"{prefix}StdDev: {format_time(result.stdev)}")
    print(f"{prefix}Throughput: {format_ops(result.ops_per_second)}")
    print(f"{prefix}Iterations: {result.iterations}")


def print_comparison(comparison: ComparisonResult):
    """Print comparison results."""
    print(f"\n{'=' * 70}")
    print(f"BENCHMARK: {comparison.benchmark_name}")
    print(f"{'=' * 70}")

    print(f"\n  RustyAML:")
    print_result(comparison.rustyaml_result)

    if comparison.pyyaml_result:
        print(f"\n  PyYAML (Pure Python):")
        print_result(comparison.pyyaml_result)
        speedup = comparison.speedup_vs_pyyaml
        print(f"\n  → RustyAML is {speedup:.2f}x faster than PyYAML (Pure Python)")

    if comparison.pyyaml_c_result:
        print(f"\n  PyYAML (C Extension - CSafeLoader):")
        print_result(comparison.pyyaml_c_result)
        speedup = comparison.speedup_vs_pyyaml_c
        print(f"\n  → RustyAML is {speedup:.2f}x faster than PyYAML (C Extension)")


# ============================================================================
# Individual Benchmarks
# ============================================================================

def benchmark_yaml_string(
    name: str,
    yaml_string: str,
    description: str = "",
) -> ComparisonResult:
    """Benchmark parsing of a YAML string."""

    print(f"\nRunning: {name}")
    if description:
        print(f"  {description}")
    print(f"  Size: {len(yaml_string):,} bytes, {yaml_string.count(chr(10)):,} lines")

    # RustyAML
    rustyaml_result = run_benchmark(
        name=name,
        func=lambda: rustyaml.safe_load(yaml_string),
    )
    rustyaml_result.library = "rustyaml"

    # PyYAML Pure Python
    pyyaml_result = None
    if HAS_PYYAML:
        pyyaml_result = run_benchmark(
            name=name,
            func=lambda: pyyaml.safe_load(yaml_string),
        )
        pyyaml_result.library = "pyyaml"

    # PyYAML C Extension
    pyyaml_c_result = None
    if HAS_PYYAML_C:
        pyyaml_c_result = run_benchmark(
            name=name,
            func=lambda: pyyaml.load(yaml_string, Loader=pyyaml.CSafeLoader),
        )
        pyyaml_c_result.library = "pyyaml_c"

    return ComparisonResult(
        benchmark_name=name,
        rustyaml_result=rustyaml_result,
        pyyaml_result=pyyaml_result,
        pyyaml_c_result=pyyaml_c_result,
    )


def benchmark_file(
    name: str,
    filepath: Path,
    description: str = "",
) -> ComparisonResult:
    """Benchmark parsing of a YAML file."""
    yaml_string = filepath.read_text()
    return benchmark_yaml_string(name, yaml_string, description)


def benchmark_batch_loading(
    name: str,
    yaml_strings: List[str],
    description: str = "",
) -> ComparisonResult:
    """Benchmark batch loading of multiple YAML documents."""

    print(f"\nRunning: {name}")
    if description:
        print(f"  {description}")
    print(f"  Documents: {len(yaml_strings):,}")

    # RustyAML batch (parallel)
    rustyaml_result = run_benchmark(
        name=name,
        func=lambda: rustyaml.safe_load_many(yaml_strings),
    )
    rustyaml_result.library = "rustyaml"

    # PyYAML sequential
    pyyaml_result = None
    if HAS_PYYAML:
        pyyaml_result = run_benchmark(
            name=name,
            func=lambda: [pyyaml.safe_load(s) for s in yaml_strings],
        )
        pyyaml_result.library = "pyyaml"

    # PyYAML C Extension sequential
    pyyaml_c_result = None
    if HAS_PYYAML_C:
        pyyaml_c_result = run_benchmark(
            name=name,
            func=lambda: [pyyaml.load(s, Loader=pyyaml.CSafeLoader) for s in yaml_strings],
        )
        pyyaml_c_result.library = "pyyaml_c"

    return ComparisonResult(
        benchmark_name=name,
        rustyaml_result=rustyaml_result,
        pyyaml_result=pyyaml_result,
        pyyaml_c_result=pyyaml_c_result,
    )


def benchmark_multi_document(
    name: str,
    yaml_string: str,
    description: str = "",
) -> ComparisonResult:
    """Benchmark parsing of multi-document YAML stream."""

    print(f"\nRunning: {name}")
    if description:
        print(f"  {description}")
    print(f"  Size: {len(yaml_string):,} bytes")

    # RustyAML
    rustyaml_result = run_benchmark(
        name=name,
        func=lambda: rustyaml.safe_load_all(yaml_string),
    )
    rustyaml_result.library = "rustyaml"

    # PyYAML
    pyyaml_result = None
    if HAS_PYYAML:
        pyyaml_result = run_benchmark(
            name=name,
            func=lambda: list(pyyaml.safe_load_all(yaml_string)),
        )
        pyyaml_result.library = "pyyaml"

    # PyYAML C Extension
    pyyaml_c_result = None
    if HAS_PYYAML_C:
        pyyaml_c_result = run_benchmark(
            name=name,
            func=lambda: list(pyyaml.load_all(yaml_string, Loader=pyyaml.CSafeLoader)),
        )
        pyyaml_c_result.library = "pyyaml_c"

    return ComparisonResult(
        benchmark_name=name,
        rustyaml_result=rustyaml_result,
        pyyaml_result=pyyaml_result,
        pyyaml_c_result=pyyaml_c_result,
    )


# ============================================================================
# Main Benchmark Suite
# ============================================================================

def run_all_benchmarks() -> List[ComparisonResult]:
    """Run the complete benchmark suite."""

    print("=" * 70)
    print("RustyAML vs PyYAML Benchmark Suite")
    print("=" * 70)
    print(f"\nRustyAML: Installed")
    print(f"PyYAML: {'Installed' if HAS_PYYAML else 'Not installed'}")
    print(f"PyYAML C Extension: {'Available' if HAS_PYYAML_C else 'Not available'}")
    print(f"\nTarget time per benchmark: {TARGET_TIME_SECONDS}s")
    print(f"Warmup iterations: {WARMUP_ITERATIONS}")

    results = []

    # -------------------------------------------------------------------------
    # Small Configs
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CATEGORY: Small Configurations")
    print("-" * 70)

    # Minimal config
    results.append(benchmark_yaml_string(
        "Minimal (1 key)",
        "key: value",
        "Single key-value pair"
    ))

    # Small file fixture
    small_config_path = FIXTURES_DIR / "small_config.yaml"
    if small_config_path.exists():
        results.append(benchmark_file(
            "Small Config File (~20 lines)",
            small_config_path,
            "Simple application configuration"
        ))

    # Small generated
    results.append(benchmark_yaml_string(
        "Flat Config (50 keys)",
        generate_flat_config(50),
        "50 key-value pairs"
    ))

    # -------------------------------------------------------------------------
    # Medium Configs
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CATEGORY: Medium Configurations")
    print("-" * 70)

    # Medium file fixture
    medium_config_path = FIXTURES_DIR / "medium_config.yaml"
    if medium_config_path.exists():
        results.append(benchmark_file(
            "Medium Config File (~200 lines)",
            medium_config_path,
            "Microservices application configuration"
        ))

    # Generated medium configs
    results.append(benchmark_yaml_string(
        "Flat Config (500 keys)",
        generate_flat_config(500),
        "500 key-value pairs"
    ))

    results.append(benchmark_yaml_string(
        "Nested Config (depth=5, breadth=4)",
        generate_nested_config(5, 4),
        "Deeply nested structure"
    ))

    results.append(benchmark_yaml_string(
        "List Config (100 items)",
        generate_list_config(100, 5),
        "List of 100 objects with 5 fields each"
    ))

    # -------------------------------------------------------------------------
    # Large Configs
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CATEGORY: Large Configurations")
    print("-" * 70)

    # Large file fixture
    large_config_path = FIXTURES_DIR / "large_config.yaml"
    if large_config_path.exists():
        results.append(benchmark_file(
            "Large Config File (~1200 lines)",
            large_config_path,
            "Kubernetes cluster configuration"
        ))

    # Kubernetes fixture
    k8s_path = FIXTURES_DIR / "kubernetes.yaml"
    if k8s_path.exists():
        results.append(benchmark_file(
            "Kubernetes Manifest",
            k8s_path,
            "Multi-document Kubernetes manifest"
        ))

    # Generated large configs
    results.append(benchmark_yaml_string(
        "Flat Config (2000 keys)",
        generate_flat_config(2000),
        "2000 key-value pairs"
    ))

    results.append(benchmark_yaml_string(
        "List Config (500 items)",
        generate_list_config(500, 8),
        "List of 500 objects with 8 fields each"
    ))

    results.append(benchmark_yaml_string(
        "Mixed Config (20 sections, 10 items each)",
        generate_mixed_config(20, 10),
        "Complex mixed structure"
    ))

    # -------------------------------------------------------------------------
    # Extra Large / Production Scale
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CATEGORY: Extra Large / Production Scale")
    print("-" * 70)

    # XL generated enterprise config
    xl_config = generate_xlarge_enterprise_config()
    results.append(benchmark_yaml_string(
        "XL Enterprise Config (~5000+ lines)",
        xl_config,
        "Enterprise platform configuration with 20 services"
    ))

    # Very large flat config
    results.append(benchmark_yaml_string(
        "Flat Config (10000 keys)",
        generate_flat_config(10000),
        "10,000 key-value pairs"
    ))

    # Very large list
    results.append(benchmark_yaml_string(
        "List Config (2000 items)",
        generate_list_config(2000, 10),
        "List of 2000 objects with 10 fields each"
    ))

    # -------------------------------------------------------------------------
    # Batch / Parallel Processing
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CATEGORY: Batch Processing")
    print("-" * 70)

    # Batch small documents
    small_docs = [f"doc: {i}\nvalue: {i * 10}" for i in range(100)]
    results.append(benchmark_batch_loading(
        "Batch Load: 100 Small Documents",
        small_docs,
        "Parallel vs sequential loading"
    ))

    # Batch medium documents
    medium_docs = [generate_flat_config(50) for _ in range(50)]
    results.append(benchmark_batch_loading(
        "Batch Load: 50 Medium Documents (50 keys each)",
        medium_docs,
        "Parallel vs sequential loading"
    ))

    # Batch large documents
    large_docs = [generate_flat_config(200) for _ in range(20)]
    results.append(benchmark_batch_loading(
        "Batch Load: 20 Large Documents (200 keys each)",
        large_docs,
        "Parallel vs sequential loading"
    ))

    # -------------------------------------------------------------------------
    # Multi-Document Streams
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CATEGORY: Multi-Document YAML Streams")
    print("-" * 70)

    results.append(benchmark_multi_document(
        "Multi-Doc: 10 Documents",
        generate_multi_document_yaml(10, 30),
        "YAML stream with 10 documents"
    ))

    results.append(benchmark_multi_document(
        "Multi-Doc: 50 Documents",
        generate_multi_document_yaml(50, 30),
        "YAML stream with 50 documents"
    ))

    results.append(benchmark_multi_document(
        "Multi-Doc: 100 Documents",
        generate_multi_document_yaml(100, 20),
        "YAML stream with 100 documents"
    ))

    return results


def print_summary(results: List[ComparisonResult]):
    """Print a summary table of all results."""

    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)

    # Header
    print(f"\n{'Benchmark':<50} {'RustyAML':<12} {'PyYAML':<12} {'PyYAML-C':<12} {'Speedup':<10}")
    print("-" * 90)

    for result in results:
        rusty_time = format_time(result.rustyaml_result.mean_time)

        pyyaml_time = "-"
        pyyaml_c_time = "-"
        speedup = "-"

        if result.pyyaml_result:
            pyyaml_time = format_time(result.pyyaml_result.mean_time)

        if result.pyyaml_c_result:
            pyyaml_c_time = format_time(result.pyyaml_c_result.mean_time)
            speedup = f"{result.speedup_vs_pyyaml_c:.2f}x"
        elif result.pyyaml_result:
            speedup = f"{result.speedup_vs_pyyaml:.2f}x"

        name = result.benchmark_name[:48]
        print(f"{name:<50} {rusty_time:<12} {pyyaml_time:<12} {pyyaml_c_time:<12} {speedup:<10}")

    # Calculate average speedup
    speedups_pyyaml = [r.speedup_vs_pyyaml for r in results if r.speedup_vs_pyyaml]
    speedups_pyyaml_c = [r.speedup_vs_pyyaml_c for r in results if r.speedup_vs_pyyaml_c]

    print("-" * 90)

    if speedups_pyyaml:
        avg_speedup = statistics.mean(speedups_pyyaml)
        print(f"\nAverage speedup vs PyYAML (Pure Python): {avg_speedup:.2f}x")

    if speedups_pyyaml_c:
        avg_speedup_c = statistics.mean(speedups_pyyaml_c)
        print(f"Average speedup vs PyYAML (C Extension): {avg_speedup_c:.2f}x")


def export_results_json(results: List[ComparisonResult], filepath: Path):
    """Export results to JSON for further analysis."""

    data = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_time_seconds": TARGET_TIME_SECONDS,
            "warmup_iterations": WARMUP_ITERATIONS,
            "pyyaml_available": HAS_PYYAML,
            "pyyaml_c_available": HAS_PYYAML_C,
        },
        "results": []
    }

    for result in results:
        entry = {
            "name": result.benchmark_name,
            "rustyaml": {
                "mean_time": result.rustyaml_result.mean_time,
                "median_time": result.rustyaml_result.median_time,
                "min_time": result.rustyaml_result.min_time,
                "max_time": result.rustyaml_result.max_time,
                "stdev": result.rustyaml_result.stdev,
                "ops_per_second": result.rustyaml_result.ops_per_second,
                "iterations": result.rustyaml_result.iterations,
            }
        }

        if result.pyyaml_result:
            entry["pyyaml"] = {
                "mean_time": result.pyyaml_result.mean_time,
                "median_time": result.pyyaml_result.median_time,
                "min_time": result.pyyaml_result.min_time,
                "max_time": result.pyyaml_result.max_time,
                "stdev": result.pyyaml_result.stdev,
                "ops_per_second": result.pyyaml_result.ops_per_second,
                "iterations": result.pyyaml_result.iterations,
            }
            entry["speedup_vs_pyyaml"] = result.speedup_vs_pyyaml

        if result.pyyaml_c_result:
            entry["pyyaml_c"] = {
                "mean_time": result.pyyaml_c_result.mean_time,
                "median_time": result.pyyaml_c_result.median_time,
                "min_time": result.pyyaml_c_result.min_time,
                "max_time": result.pyyaml_c_result.max_time,
                "stdev": result.pyyaml_c_result.stdev,
                "ops_per_second": result.pyyaml_c_result.ops_per_second,
                "iterations": result.pyyaml_c_result.iterations,
            }
            entry["speedup_vs_pyyaml_c"] = result.speedup_vs_pyyaml_c

        data["results"].append(entry)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults exported to: {filepath}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark RustyAML vs PyYAML"
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmarks (shorter target time)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed results for each benchmark",
    )

    args = parser.parse_args()

    if args.quick:
        global TARGET_TIME_SECONDS
        TARGET_TIME_SECONDS = 0.5

    # Run all benchmarks
    results = run_all_benchmarks()

    # Print detailed results if verbose
    if args.verbose:
        for result in results:
            print_comparison(result)

    # Print summary
    print_summary(results)

    # Export to JSON if requested
    if args.json:
        export_results_json(results, Path(args.json))

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
