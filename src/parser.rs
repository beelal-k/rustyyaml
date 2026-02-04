//! Core YAML parsing logic
//!
//! This module wraps serde_yaml and adds:
//! - Safety checks (reject dangerous tags)
//! - Better error messages
//! - Python type conversion

use pyo3::prelude::*;
use serde_yaml::Value;

use crate::error::YAMLError;
use crate::safe;
use crate::types::yaml_to_python;

/// Parse a YAML string safely (no code execution)
///
/// This is the main entry point for safe_load()
///
/// # Arguments
/// * `yaml_str` - YAML content as UTF-8 string
///
/// # Returns
/// * `PyObject` - Python object (dict, list, str, int, float, bool, None)
///
/// # Errors
/// * Parse errors (syntax issues)
/// * Unsafe tags (!!python/object, etc.)
/// * UTF-8 decoding errors
pub fn parse_safe(py: Python, yaml_str: &str) -> PyResult<PyObject> {
    // Step 1: Quick scan for unsafe patterns in raw string
    // This catches tags that serde_yaml might silently ignore
    safe::quick_safety_check(yaml_str)?;

    // Step 2: Parse YAML string to serde_yaml::Value
    // This is pure Rust - no Python interaction yet
    let value: Value = serde_yaml::from_str(yaml_str).map_err(YAMLError::from)?;

    // Step 3: Check for unsafe tags in parsed structure
    safe::check_safety(&value)?;

    // Step 4: Convert to Python object
    yaml_to_python(py, &value)
}

/// Parse a YAML string without safety checks (DANGEROUS!)
///
/// This allows custom tags like !!python/object
/// Only use this if you TRUST the YAML source
///
/// # Safety
/// This can execute arbitrary Python code embedded in YAML
pub fn parse_unsafe(py: Python, yaml_str: &str) -> PyResult<PyObject> {
    // For now, same as safe_load but we'll add custom tag handlers later
    // TODO: Implement custom Python object deserialization
    let value: Value = serde_yaml::from_str(yaml_str).map_err(YAMLError::from)?;

    // Skip safety check for unsafe_load
    yaml_to_python(py, &value)
}

/// Parse multiple YAML documents from a single string
///
/// YAML allows multiple documents separated by '---'
/// Example:
/// ```yaml
/// doc: 1
/// ---
/// doc: 2
/// ---
/// doc: 3
/// ```
pub fn parse_all(py: Python, yaml_str: &str) -> PyResult<Vec<PyObject>> {
    // Quick scan for unsafe patterns in raw string first
    safe::quick_safety_check(yaml_str)?;

    let mut documents = Vec::new();

    // serde_yaml provides a Deserializer that can handle multiple documents
    for document in serde_yaml::Deserializer::from_str(yaml_str) {
        let value: Value = serde::Deserialize::deserialize(document).map_err(YAMLError::from)?;

        // Check safety for each document
        safe::check_safety(&value)?;

        let py_obj = yaml_to_python(py, &value)?;
        documents.push(py_obj);
    }

    Ok(documents)
}

/// Parse multiple YAML documents without safety checks
pub fn parse_all_unsafe(py: Python, yaml_str: &str) -> PyResult<Vec<PyObject>> {
    let mut documents = Vec::new();

    for document in serde_yaml::Deserializer::from_str(yaml_str) {
        let value: Value = serde::Deserialize::deserialize(document).map_err(YAMLError::from)?;
        let py_obj = yaml_to_python(py, &value)?;
        documents.push(py_obj);
    }

    Ok(documents)
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::{PyDict, PyList};

    #[test]
    fn test_parse_simple_dict() {
        Python::with_gil(|py| {
            let yaml = "key: value";
            let result = parse_safe(py, yaml).unwrap();

            // Should be a dict
            assert!(result.bind(py).downcast::<PyDict>().is_ok());
        });
    }

    #[test]
    fn test_parse_list() {
        Python::with_gil(|py| {
            let yaml = "- item1\n- item2\n- item3";
            let result = parse_safe(py, yaml).unwrap();

            // Should be a list
            assert!(result.bind(py).downcast::<PyList>().is_ok());
        });
    }

    #[test]
    fn test_parse_nested_structure() {
        Python::with_gil(|py| {
            let yaml = r#"
database:
  host: localhost
  port: 5432
  enabled: true
"#;
            let result = parse_safe(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            // Check nested structure
            let db = dict.get_item("database").unwrap().unwrap();
            let db_dict = db.downcast::<PyDict>().unwrap();
            assert!(db_dict.get_item("host").is_ok());
        });
    }

    #[test]
    fn test_parse_multiple_documents() {
        Python::with_gil(|py| {
            let yaml = "doc: 1\n---\ndoc: 2\n---\ndoc: 3";
            let results = parse_all(py, yaml).unwrap();

            assert_eq!(results.len(), 3);
        });
    }

    #[test]
    fn test_parse_empty_string() {
        Python::with_gil(|py| {
            let yaml = "";
            let result = parse_safe(py, yaml).unwrap();

            // Empty YAML should return None
            assert!(result.is_none(py));
        });
    }

    #[test]
    fn test_parse_null() {
        Python::with_gil(|py| {
            let yaml = "null";
            let result = parse_safe(py, yaml).unwrap();

            assert!(result.is_none(py));
        });
    }

    #[test]
    fn test_parse_numbers() {
        Python::with_gil(|py| {
            let yaml = r#"
integer: 42
negative: -17
float: 3.14
scientific: 1.23e-4
"#;
            let result = parse_safe(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            let int_val: i64 = dict
                .get_item("integer")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(int_val, 42);

            let neg_val: i64 = dict
                .get_item("negative")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(neg_val, -17);
        });
    }

    #[test]
    fn test_parse_booleans() {
        Python::with_gil(|py| {
            let yaml = r#"
yes_val: yes
no_val: no
true_val: true
false_val: false
"#;
            let result = parse_safe(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            let yes: bool = dict
                .get_item("yes_val")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            assert!(yes);

            let no: bool = dict.get_item("no_val").unwrap().unwrap().extract().unwrap();
            assert!(!no);
        });
    }

    #[test]
    fn test_parse_invalid_yaml() {
        Python::with_gil(|py| {
            let yaml = "key: : invalid";
            let result = parse_safe(py, yaml);

            assert!(result.is_err());
        });
    }

    #[test]
    fn test_parse_multiline_string() {
        Python::with_gil(|py| {
            let yaml = r#"
text: |
  This is a
  multiline string
"#;
            let result = parse_safe(py, yaml).unwrap();
            let dict = result.bind(py).downcast::<PyDict>().unwrap();

            let text: String = dict.get_item("text").unwrap().unwrap().extract().unwrap();
            assert!(text.contains("multiline"));
        });
    }
}
