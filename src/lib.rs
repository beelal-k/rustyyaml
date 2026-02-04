//! RustyAML: Fast, safe YAML parser for Python
//!
//! This module exposes Rust functions to Python via PyO3
//!
//! # Features
//! - 10-100x faster than pure Python PyYAML
//! - 100% safe by default (no code execution)
//! - Drop-in replacement for PyYAML
//! - Parallel batch loading for multiple files

mod batch;
mod error;
mod parser;
mod safe;
mod types;

use pyo3::prelude::*;

/// Parse YAML string safely (no code execution)
///
/// # Arguments
/// * `yaml_str` - YAML content as string
///
/// # Returns
/// Python object (dict, list, str, int, float, bool, None)
///
/// # Example
/// ```python
/// import rustyaml
/// data = rustyaml.safe_load("key: value")
/// print(data)  # {'key': 'value'}
/// ```
#[pyfunction]
fn safe_load(py: Python, yaml_str: &str) -> PyResult<PyObject> {
    parser::parse_safe(py, yaml_str)
}

/// Parse YAML string without safety checks (DANGEROUS!)
///
/// This allows custom tags like !!python/object
/// Only use if you TRUST the YAML source
///
/// # Arguments
/// * `yaml_str` - YAML content as string
///
/// # Returns
/// Python object
///
/// # Warning
/// This can execute arbitrary code embedded in YAML
#[pyfunction]
fn unsafe_load(py: Python, yaml_str: &str) -> PyResult<PyObject> {
    parser::parse_unsafe(py, yaml_str)
}

/// Parse multiple YAML documents from a single string
///
/// # Arguments
/// * `yaml_str` - YAML content with documents separated by '---'
///
/// # Returns
/// List of Python objects
///
/// # Example
/// ```python
/// import rustyaml
/// yaml_str = '''
/// doc: 1
/// ---
/// doc: 2
/// ---
/// doc: 3
/// '''
/// docs = rustyaml.load_all(yaml_str)
/// print(len(docs))  # 3
/// ```
#[pyfunction]
fn load_all(py: Python, yaml_str: &str) -> PyResult<Vec<PyObject>> {
    parser::parse_all(py, yaml_str)
}

/// Parse multiple YAML documents without safety checks
#[pyfunction]
fn load_all_unsafe(py: Python, yaml_str: &str) -> PyResult<Vec<PyObject>> {
    parser::parse_all_unsafe(py, yaml_str)
}

/// Get the version string
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Python module definition
///
/// This is what Python sees when it does `import rustyaml`
#[pymodule]
fn rustyaml(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Core functions
    m.add_function(wrap_pyfunction!(safe_load, m)?)?;
    m.add_function(wrap_pyfunction!(unsafe_load, m)?)?;
    m.add_function(wrap_pyfunction!(load_all, m)?)?;
    m.add_function(wrap_pyfunction!(load_all_unsafe, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;

    // Batch operations
    m.add_function(wrap_pyfunction!(batch::safe_load_many, m)?)?;
    m.add_function(wrap_pyfunction!(batch::unsafe_load_many, m)?)?;
    m.add_function(wrap_pyfunction!(batch::load_directory, m)?)?;
    m.add_function(wrap_pyfunction!(batch::load_directory_unsafe, m)?)?;

    // Add version constant
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::PyDict;

    #[test]
    fn test_safe_load_simple() {
        Python::with_gil(|py| {
            let yaml = "key: value";
            let result = safe_load(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            let val: String = dict.get_item("key").unwrap().unwrap().extract().unwrap();
            assert_eq!(val, "value");
        });
    }

    #[test]
    fn test_load_all_multiple_docs() {
        Python::with_gil(|py| {
            let yaml = "doc: 1\n---\ndoc: 2\n---\ndoc: 3";
            let results = load_all(py, yaml).unwrap();
            assert_eq!(results.len(), 3);
        });
    }

    #[test]
    fn test_version() {
        let v = version();
        assert!(!v.is_empty());
    }

    #[test]
    fn test_safe_load_nested() {
        Python::with_gil(|py| {
            let yaml = r#"
database:
  host: localhost
  port: 5432
"#;
            let result = safe_load(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            let db = dict.get_item("database").unwrap().unwrap();
            let db_dict = db.downcast::<PyDict>().unwrap();

            let host: String = db_dict
                .get_item("host")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(host, "localhost");

            let port: i64 = db_dict
                .get_item("port")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(port, 5432);
        });
    }

    #[test]
    fn test_safe_load_list() {
        Python::with_gil(|py| {
            let yaml = "- item1\n- item2\n- item3";
            let result = safe_load(py, yaml).unwrap();

            let list: Vec<String> = result.extract(py).unwrap();
            assert_eq!(list, vec!["item1", "item2", "item3"]);
        });
    }

    #[test]
    fn test_safe_load_empty() {
        Python::with_gil(|py| {
            let yaml = "";
            let result = safe_load(py, yaml).unwrap();
            assert!(result.is_none(py));
        });
    }

    #[test]
    fn test_safe_load_rejects_unsafe_tags() {
        Python::with_gil(|py| {
            let yaml = "!!python/object/apply:os.system ['echo bad']";
            let result = safe_load(py, yaml);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_unsafe_load_allows_regular_yaml() {
        Python::with_gil(|py| {
            let yaml = "key: value";
            let result = unsafe_load(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            let val: String = dict.get_item("key").unwrap().unwrap().extract().unwrap();
            assert_eq!(val, "value");
        });
    }
}
