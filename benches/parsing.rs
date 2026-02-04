//! Performance benchmarks for RustyAML
//!
//! Run with: cargo bench

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Benchmark: Simple key-value pair
fn bench_simple_dict(c: &mut Criterion) {
    let yaml = "key: value";

    c.bench_function("simple_dict", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(yaml)).unwrap();
            black_box(value)
        })
    });
}

/// Benchmark: Nested structure (realistic config file)
fn bench_nested_config(c: &mut Criterion) {
    let yaml = r#"
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
  pool:
    min_size: 5
    max_size: 20
server:
  host: 0.0.0.0
  port: 8080
  workers: 4
logging:
  level: info
  format: json
"#;

    c.bench_function("nested_config", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(yaml)).unwrap();
            black_box(value)
        })
    });
}

/// Benchmark: Large list (1000 items)
fn bench_large_list(c: &mut Criterion) {
    let mut yaml = String::new();
    for i in 0..1000 {
        yaml.push_str(&format!("- item{}\n", i));
    }

    c.bench_function("large_list_1000", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(&yaml)).unwrap();
            black_box(value)
        })
    });
}

/// Benchmark: Kubernetes manifest (realistic production file)
fn bench_kubernetes_manifest(c: &mut Criterion) {
    let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
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
          value: "value2"
        resources:
          limits:
            memory: "128Mi"
            cpu: "500m"
          requests:
            memory: "64Mi"
            cpu: "250m"
"#;

    c.bench_function("kubernetes_manifest", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(yaml)).unwrap();
            black_box(value)
        })
    });
}

/// Benchmark: Scaling test (varying document sizes)
fn bench_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("scaling");

    for size in [10, 100, 1000, 10000].iter() {
        let mut yaml = String::new();
        for i in 0..*size {
            yaml.push_str(&format!("key{}: value{}\n", i, i));
        }

        group.bench_with_input(BenchmarkId::from_parameter(size), &yaml, |b, yaml| {
            b.iter(|| {
                let value: serde_yaml::Value = serde_yaml::from_str(black_box(yaml)).unwrap();
                black_box(value)
            })
        });
    }

    group.finish();
}

/// Benchmark: Multiple documents
fn bench_multiple_documents(c: &mut Criterion) {
    let yaml = r#"
doc: 1
---
doc: 2
---
doc: 3
---
doc: 4
---
doc: 5
"#;

    c.bench_function("multiple_documents", |b| {
        b.iter(|| {
            let mut docs = Vec::new();
            for document in serde_yaml::Deserializer::from_str(black_box(yaml)) {
                let value: serde_yaml::Value = serde::Deserialize::deserialize(document).unwrap();
                docs.push(value);
            }
            black_box(docs)
        })
    });
}

/// Benchmark: Complex nested structure
fn bench_complex_nested(c: &mut Criterion) {
    let yaml = r#"
company:
  name: Acme Corp
  founded: 1990
  public: true
  departments:
    - name: Engineering
      budget: 1000000
      employees:
        - name: Alice
          role: Senior Engineer
          skills:
            - Python
            - Rust
            - Go
          projects:
            - name: Project Alpha
              status: active
            - name: Project Beta
              status: completed
        - name: Bob
          role: Junior Engineer
          skills:
            - JavaScript
            - TypeScript
    - name: Marketing
      budget: 500000
      employees:
        - name: Charlie
          role: Marketing Manager
          campaigns:
            - Q1 Campaign
            - Q2 Campaign
  locations:
    headquarters:
      city: San Francisco
      country: USA
      employees: 500
    branch:
      city: London
      country: UK
      employees: 100
"#;

    c.bench_function("complex_nested", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(yaml)).unwrap();
            black_box(value)
        })
    });
}

/// Benchmark: Parallel batch loading
fn bench_parallel_batch(c: &mut Criterion) {
    use rayon::prelude::*;

    let yamls: Vec<String> = (0..100).map(|i| format!("key: value{}", i)).collect();

    let mut group = c.benchmark_group("batch_loading");

    group.bench_function("sequential_100", |b| {
        b.iter(|| {
            let results: Vec<serde_yaml::Value> = yamls
                .iter()
                .map(|yaml| serde_yaml::from_str(yaml).unwrap())
                .collect();
            black_box(results)
        })
    });

    group.bench_function("parallel_100", |b| {
        b.iter(|| {
            let results: Vec<serde_yaml::Value> = yamls
                .par_iter()
                .map(|yaml| serde_yaml::from_str(yaml).unwrap())
                .collect();
            black_box(results)
        })
    });

    group.finish();
}

/// Benchmark: String interning effect
fn bench_string_interning(c: &mut Criterion) {
    // Short strings (should benefit from interning)
    let short_yaml = r#"
a: 1
b: 2
c: 3
d: 4
e: 5
"#;

    // Long strings (no interning benefit)
    let long_yaml = r#"
this_is_a_very_long_key_name: this_is_a_very_long_value_string
another_really_long_key_here: and_another_long_value_to_match
yet_another_lengthy_key_name: with_corresponding_lengthy_value
"#;

    let mut group = c.benchmark_group("string_lengths");

    group.bench_function("short_strings", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(short_yaml)).unwrap();
            black_box(value)
        })
    });

    group.bench_function("long_strings", |b| {
        b.iter(|| {
            let value: serde_yaml::Value = serde_yaml::from_str(black_box(long_yaml)).unwrap();
            black_box(value)
        })
    });

    group.finish();
}

/// Benchmark: Full Python integration (requires GIL)
fn bench_python_integration(c: &mut Criterion) {
    pyo3::prepare_freethreaded_python();

    let yaml = r#"
database:
  host: localhost
  port: 5432
server:
  host: 0.0.0.0
  port: 8080
"#;

    c.bench_function("python_integration", |b| {
        b.iter(|| {
            Python::with_gil(|py| {
                let value: serde_yaml::Value = serde_yaml::from_str(black_box(yaml)).unwrap();
                let dict = PyDict::new(py);
                // Simulate conversion overhead
                for (k, v) in value.as_mapping().unwrap() {
                    if let Some(key) = k.as_str() {
                        dict.set_item(key, format!("{:?}", v)).unwrap();
                    }
                }
                black_box(dict)
            })
        })
    });
}

criterion_group!(
    benches,
    bench_simple_dict,
    bench_nested_config,
    bench_large_list,
    bench_kubernetes_manifest,
    bench_scaling,
    bench_multiple_documents,
    bench_complex_nested,
    bench_parallel_batch,
    bench_string_interning,
    bench_python_integration,
);
criterion_main!(benches);
