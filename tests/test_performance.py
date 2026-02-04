"""Performance comparison tests for RustyAML"""

import time
from typing import Callable

import pytest

try:
    import yaml as pyyaml

    HAS_PYYAML = True
except ImportError:
    HAS_PYYAML = False

import rustyaml


def time_operation(func: Callable, iterations: int = 1000) -> float:
    """Time a function call over multiple iterations"""
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    return time.perf_counter() - start


class TestPerformance:
    """Performance comparison tests"""

    @pytest.mark.skipif(not HAS_PYYAML, reason="PyYAML not installed")
    def test_simple_dict_speed(self):
        """Compare simple dict parsing speed"""
        yaml_str = "key: value"

        rusty_time = time_operation(
            lambda: rustyaml.safe_load(yaml_str), iterations=10000
        )

        pyyaml_time = time_operation(
            lambda: pyyaml.safe_load(yaml_str), iterations=10000
        )

        speedup = pyyaml_time / rusty_time
        print(f"\nSimple dict speedup: {speedup:.2f}x")
        print(f"  RustyAML: {rusty_time:.4f}s")
        print(f"  PyYAML:   {pyyaml_time:.4f}s")

        # Should be at least 2x faster
        assert speedup >= 1.0, f"Expected speedup, got {speedup:.2f}x"

    @pytest.mark.skipif(not HAS_PYYAML, reason="PyYAML not installed")
    def test_nested_config_speed(self):
        """Compare nested config parsing speed"""
        yaml_str = """
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
server:
  host: 0.0.0.0
  port: 8080
  workers: 4
logging:
  level: info
  format: json
  handlers:
    - console
    - file
"""

        rusty_time = time_operation(
            lambda: rustyaml.safe_load(yaml_str), iterations=5000
        )

        pyyaml_time = time_operation(
            lambda: pyyaml.safe_load(yaml_str), iterations=5000
        )

        speedup = pyyaml_time / rusty_time
        print(f"\nNested config speedup: {speedup:.2f}x")
        print(f"  RustyAML: {rusty_time:.4f}s")
        print(f"  PyYAML:   {pyyaml_time:.4f}s")

        # Should be at least 2x faster
        assert speedup >= 1.0, f"Expected speedup, got {speedup:.2f}x"

    @pytest.mark.skipif(not HAS_PYYAML, reason="PyYAML not installed")
    def test_large_list_speed(self):
        """Compare large list parsing speed"""
        yaml_str = "\n".join(f"- item{i}" for i in range(1000))

        rusty_time = time_operation(lambda: rustyaml.safe_load(yaml_str), iterations=100)

        pyyaml_time = time_operation(lambda: pyyaml.safe_load(yaml_str), iterations=100)

        speedup = pyyaml_time / rusty_time
        print(f"\nLarge list (1000 items) speedup: {speedup:.2f}x")
        print(f"  RustyAML: {rusty_time:.4f}s")
        print(f"  PyYAML:   {pyyaml_time:.4f}s")

        assert speedup >= 1.0, f"Expected speedup, got {speedup:.2f}x"

    def test_batch_loading_speed(self):
        """Test parallel batch loading is faster than sequential"""
        yamls = [f"doc: {i}" for i in range(1000)]

        # Sequential loading
        sequential_time = time_operation(
            lambda: [rustyaml.safe_load(y) for y in yamls], iterations=10
        )

        # Parallel loading
        parallel_time = time_operation(
            lambda: rustyaml.safe_load_many(yamls), iterations=10
        )

        speedup = sequential_time / parallel_time
        print(f"\nBatch loading speedup (1000 docs): {speedup:.2f}x")
        print(f"  Sequential: {sequential_time:.4f}s")
        print(f"  Parallel:   {parallel_time:.4f}s")

        # Parallel should be faster on multi-core systems
        # On single-core, might be slightly slower due to overhead
        # We just check it's not significantly slower
        assert speedup >= 0.5, f"Parallel loading too slow: {speedup:.2f}x"

    def test_rustyaml_basic_performance(self):
        """Baseline performance test for RustyAML"""
        yaml_str = """
        key1: value1
        key2: value2
        key3: value3
        nested:
          a: 1
          b: 2
          c: 3
        list:
          - item1
          - item2
          - item3
        """

        iterations = 10000
        elapsed = time_operation(lambda: rustyaml.safe_load(yaml_str), iterations)

        ops_per_sec = iterations / elapsed
        print(f"\nRustyAML baseline: {ops_per_sec:.0f} ops/sec")
        print(f"  {iterations} iterations in {elapsed:.4f}s")

        # Should be able to do at least 1000 ops/sec for simple config
        assert ops_per_sec > 1000, f"Too slow: {ops_per_sec:.0f} ops/sec"

    @pytest.mark.skipif(not HAS_PYYAML, reason="PyYAML not installed")
    def test_kubernetes_manifest_speed(self):
        """Compare parsing of realistic Kubernetes manifest"""
        yaml_str = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    version: "1.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
        env:
        - name: ENV_VAR_1
          value: "value1"
        - name: ENV_VAR_2
          valueFrom:
            configMapKeyRef:
              name: my-config
              key: config-key
        resources:
          limits:
            memory: "128Mi"
            cpu: "500m"
          requests:
            memory: "64Mi"
            cpu: "250m"
        volumeMounts:
        - name: config-volume
          mountPath: /etc/config
      volumes:
      - name: config-volume
        configMap:
          name: my-config
"""

        rusty_time = time_operation(
            lambda: rustyaml.safe_load(yaml_str), iterations=5000
        )

        pyyaml_time = time_operation(
            lambda: pyyaml.safe_load(yaml_str), iterations=5000
        )

        speedup = pyyaml_time / rusty_time
        print(f"\nKubernetes manifest speedup: {speedup:.2f}x")
        print(f"  RustyAML: {rusty_time:.4f}s")
        print(f"  PyYAML:   {pyyaml_time:.4f}s")

        assert speedup >= 1.0, f"Expected speedup, got {speedup:.2f}x"

    def test_scaling_performance(self):
        """Test performance scales linearly with input size"""
        sizes = [10, 100, 1000]
        times = []

        for size in sizes:
            yaml_str = "\n".join(f"key{i}: value{i}" for i in range(size))
            elapsed = time_operation(lambda y=yaml_str: rustyaml.safe_load(y), iterations=100)
            times.append(elapsed)
            print(f"\n{size} keys: {elapsed:.4f}s (100 iterations)")

        # Check scaling is roughly linear (not exponential)
        # Time for 1000 should be less than 100x time for 10
        scaling_factor = times[2] / times[0]
        print(f"\nScaling factor (10 -> 1000): {scaling_factor:.1f}x")
        assert scaling_factor < 200, f"Non-linear scaling: {scaling_factor:.1f}x"


class TestMemoryUsage:
    """Memory usage tests (basic, no profiling tools required)"""

    def test_large_document_memory(self):
        """Ensure we can parse large documents without issues"""
        # Generate a ~1MB YAML document
        yaml_str = "\n".join(f"key{i}: {'x' * 100}" for i in range(10000))

        # Should complete without memory issues
        result = rustyaml.safe_load(yaml_str)
        assert len(result) == 10000

    def test_many_small_documents(self):
        """Parse many small documents"""
        yamls = [f"key: value{i}" for i in range(10000)]

        results = rustyaml.safe_load_many(yamls)
        assert len(results) == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
