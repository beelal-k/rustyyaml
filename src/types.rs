//! Type conversion between Rust (serde_yaml) and Python (PyO3)
//!
//! YAML supports these data types per YAML 1.2 spec:
//! - Scalars: null, bool, int, float, string
//! - Collections: sequence (list), mapping (dict)
//! - Tags: Custom type annotations (we reject these in safe mode)

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat, PyList, PyString};
use serde_yaml::Value;

use crate::error::YAMLError;

/// Convert a serde_yaml::Value to a Python object
///
/// This is the critical path - every YAML element passes through here.
/// Performance notes:
/// - PyString::new() copies the string (unavoidable FFI cost)
/// - PyDict::new() allocates on Python heap
/// - We use intern_bound() for small strings (Python caches them)
pub fn yaml_to_python(py: Python, value: &Value) -> PyResult<PyObject> {
    match value {
        // Null becomes None
        Value::Null => Ok(py.None()),

        // Booleans
        Value::Bool(b) => Ok(b.to_object(py)),

        // Numbers (YAML allows arbitrary precision, Python has int/float)
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                // Try as i64 first (most common case)
                Ok(i.to_object(py))
            } else if let Some(u) = n.as_u64() {
                // Large unsigned integers
                Ok(u.to_object(py))
            } else if let Some(f) = n.as_f64() {
                // Floating point
                Ok(PyFloat::new_bound(py, f).into())
            } else {
                // Shouldn't happen with serde_yaml, but be defensive
                Err(YAMLError::invalid_number(n.to_string()).into())
            }
        }

        // Strings (most common case - optimize this)
        Value::String(s) => {
            // For short strings (<10 chars), use interning (Python caches these)
            if s.len() < 10 {
                Ok(PyString::intern_bound(py, s).into())
            } else {
                Ok(PyString::new_bound(py, s).into())
            }
        }

        // Sequences (YAML lists → Python lists)
        Value::Sequence(seq) => {
            let list = PyList::empty_bound(py);
            for item in seq {
                // Recursive conversion
                let py_item = yaml_to_python(py, item)?;
                list.append(py_item)?;
            }
            Ok(list.into())
        }

        // Mappings (YAML maps → Python dicts)
        // CRITICAL: Must preserve insertion order (YAML 1.2 spec requirement)
        Value::Mapping(map) => {
            let dict = PyDict::new_bound(py);
            for (k, v) in map {
                let py_key = yaml_to_python(py, k)?;
                let py_val = yaml_to_python(py, v)?;
                dict.set_item(py_key, py_val)?;
            }
            Ok(dict.into())
        }

        // Tagged values (!!python/object, etc.)
        // These are DANGEROUS - reject in safe mode
        Value::Tagged(tagged) => Err(YAMLError::unsafe_tag(tagged.tag.to_string()).into()),
    }
}

/// Convert Python object to YAML Value (for dump/emit - Phase 2 feature)
///
/// Not implementing this in MVP, but here's the signature for future:
#[allow(dead_code)]
pub fn python_to_yaml(_py: Python, _obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    // TODO: Implement in Phase 2 (YAML emission)
    // Priority: Lists, Dicts, Scalars
    // Challenge: Handle Python custom objects safely
    unimplemented!("YAML emission not yet implemented")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_null_conversion() {
        Python::with_gil(|py| {
            let yaml_null = Value::Null;
            let py_none = yaml_to_python(py, &yaml_null).unwrap();
            assert!(py_none.is_none(py));
        });
    }

    #[test]
    fn test_string_interning() {
        Python::with_gil(|py| {
            // Short strings should use interned storage
            let yaml_str = Value::String("key".to_string());
            let py_str = yaml_to_python(py, &yaml_str).unwrap();

            // Verify it's a string
            assert!(py_str.bind(py).downcast::<PyString>().is_ok());
        });
    }

    #[test]
    fn test_boolean_conversion() {
        Python::with_gil(|py| {
            let yaml_true = Value::Bool(true);
            let yaml_false = Value::Bool(false);

            let py_true = yaml_to_python(py, &yaml_true).unwrap();
            let py_false = yaml_to_python(py, &yaml_false).unwrap();

            assert!(py_true.extract::<bool>(py).unwrap());
            assert!(!py_false.extract::<bool>(py).unwrap());
        });
    }

    #[test]
    fn test_integer_conversion() {
        Python::with_gil(|py| {
            let yaml_int = Value::Number(serde_yaml::Number::from(42));
            let py_int = yaml_to_python(py, &yaml_int).unwrap();

            assert_eq!(py_int.extract::<i64>(py).unwrap(), 42);
        });
    }

    #[test]
    fn test_float_conversion() {
        Python::with_gil(|py| {
            let yaml_float = Value::Number(serde_yaml::Number::from(3.14));
            let py_float = yaml_to_python(py, &yaml_float).unwrap();

            let value: f64 = py_float.extract(py).unwrap();
            assert!((value - 3.14).abs() < 0.001);
        });
    }

    #[test]
    fn test_list_conversion() {
        Python::with_gil(|py| {
            let yaml_list = Value::Sequence(vec![
                Value::String("a".to_string()),
                Value::String("b".to_string()),
                Value::String("c".to_string()),
            ]);
            let py_list = yaml_to_python(py, &yaml_list).unwrap();

            let list = py_list.bind(py).downcast::<PyList>().unwrap();
            assert_eq!(list.len(), 3);
        });
    }

    #[test]
    fn test_dict_conversion() {
        Python::with_gil(|py| {
            let mut map = serde_yaml::Mapping::new();
            map.insert(
                Value::String("key".to_string()),
                Value::String("value".to_string()),
            );
            let yaml_dict = Value::Mapping(map);
            let py_dict = yaml_to_python(py, &yaml_dict).unwrap();

            let dict = py_dict.bind(py).downcast::<PyDict>().unwrap();
            assert_eq!(dict.len(), 1);
        });
    }
}
