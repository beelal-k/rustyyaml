//! Batch operations for parsing multiple YAML documents in parallel
//!
//! This is the "killer feature" that PyYAML doesn't have.
//! Use cases:
//! - CI/CD: Parse 1000 GitHub Actions workflow files
//! - Kubernetes: Load all manifests in a directory
//! - Config validation: Check 100 config files at once

use pyo3::prelude::*;
use rayon::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};

use crate::error::YAMLError;
use crate::safe;
use crate::types::yaml_to_python;

/// Parse multiple YAML strings in parallel
///
/// This uses rayon to parallelize across CPU cores.
/// Each YAML string is parsed independently.
///
/// # Arguments
/// * `yaml_strings` - Vec of YAML content strings
///
/// # Returns
/// * `Vec<PyObject>` - Parsed Python objects (same order as input)
///
/// # Errors
/// * Returns error for the FIRST failed parse
/// * Other documents may have been parsed successfully
///
/// # Example
/// ```python
/// import rustyaml
/// yamls = ["doc: 1", "doc: 2", "doc: 3"]
/// results = rustyaml.safe_load_many(yamls)
/// # Parses all 3 in parallel
/// ```
#[pyfunction]
pub fn safe_load_many(py: Python, yaml_strings: Vec<String>) -> PyResult<Vec<PyObject>> {
    // Parse all YAML strings in parallel using rayon
    // We collect into Results first, then convert to PyObjects
    let parsed_values: Result<Vec<_>, YAMLError> = py.allow_threads(|| {
        yaml_strings
            .par_iter()
            .map(|yaml_str| {
                // Parse YAML to serde_yaml::Value (pure Rust, no GIL needed)
                let value: serde_yaml::Value =
                    serde_yaml::from_str(yaml_str).map_err(YAMLError::from)?;

                // Check safety
                safe::check_safety(&value)?;

                Ok(value)
            })
            .collect()
    });

    // Now convert to Python objects (requires GIL)
    let values = parsed_values?;
    values
        .iter()
        .map(|value| yaml_to_python(py, value))
        .collect()
}

/// Parse multiple YAML strings in parallel without safety checks
#[pyfunction]
pub fn unsafe_load_many(py: Python, yaml_strings: Vec<String>) -> PyResult<Vec<PyObject>> {
    let parsed_values: Result<Vec<_>, YAMLError> = py.allow_threads(|| {
        yaml_strings
            .par_iter()
            .map(|yaml_str| {
                let value: serde_yaml::Value =
                    serde_yaml::from_str(yaml_str).map_err(YAMLError::from)?;
                Ok(value)
            })
            .collect()
    });

    let values = parsed_values?;
    values
        .iter()
        .map(|value| yaml_to_python(py, value))
        .collect()
}

/// Load all YAML files from a directory in parallel
///
/// # Arguments
/// * `directory` - Path to directory containing .yaml/.yml files
/// * `recursive` - If true, search subdirectories
///
/// # Returns
/// * List of (filename, parsed_data) tuples
///
/// # Example
/// ```python
/// results = rustyaml.load_directory("./configs", recursive=True)
/// for filename, data in results:
///     print(f"{filename}: {data}")
/// ```
#[pyfunction]
#[pyo3(signature = (directory, recursive=false))]
pub fn load_directory(
    py: Python,
    directory: String,
    recursive: bool,
) -> PyResult<Vec<(String, PyObject)>> {
    let dir_path = Path::new(&directory);
    if !dir_path.is_dir() {
        return Err(YAMLError::FileNotFound { path: directory }.into());
    }

    // Collect all YAML files
    let mut yaml_files = Vec::new();
    collect_yaml_files(dir_path, recursive, &mut yaml_files)?;

    // Read and parse in parallel
    let parsed_results: Result<Vec<_>, YAMLError> = py.allow_threads(|| {
        yaml_files
            .par_iter()
            .map(|path| {
                // Read file
                let content = fs::read_to_string(path).map_err(|e| YAMLError::ParseError {
                    line: 0,
                    col: 0,
                    message: format!("Failed to read {}: {}", path.display(), e),
                })?;

                // Parse YAML
                let value: serde_yaml::Value =
                    serde_yaml::from_str(&content).map_err(YAMLError::from)?;

                // Check safety
                safe::check_safety(&value)?;

                Ok((path.to_string_lossy().to_string(), value))
            })
            .collect()
    });

    // Convert to Python objects
    let results = parsed_results?;
    results
        .into_iter()
        .map(|(path, value)| {
            let py_obj = yaml_to_python(py, &value)?;
            Ok((path, py_obj))
        })
        .collect()
}

/// Load all YAML files from a directory without safety checks
#[pyfunction]
#[pyo3(signature = (directory, recursive=false))]
pub fn load_directory_unsafe(
    py: Python,
    directory: String,
    recursive: bool,
) -> PyResult<Vec<(String, PyObject)>> {
    let dir_path = Path::new(&directory);
    if !dir_path.is_dir() {
        return Err(YAMLError::FileNotFound { path: directory }.into());
    }

    let mut yaml_files = Vec::new();
    collect_yaml_files(dir_path, recursive, &mut yaml_files)?;

    let parsed_results: Result<Vec<_>, YAMLError> = py.allow_threads(|| {
        yaml_files
            .par_iter()
            .map(|path| {
                let content = fs::read_to_string(path).map_err(|e| YAMLError::ParseError {
                    line: 0,
                    col: 0,
                    message: format!("Failed to read {}: {}", path.display(), e),
                })?;

                let value: serde_yaml::Value =
                    serde_yaml::from_str(&content).map_err(YAMLError::from)?;

                Ok((path.to_string_lossy().to_string(), value))
            })
            .collect()
    });

    let results = parsed_results?;
    results
        .into_iter()
        .map(|(path, value)| {
            let py_obj = yaml_to_python(py, &value)?;
            Ok((path, py_obj))
        })
        .collect()
}

/// Helper: Recursively collect all .yaml and .yml files
fn collect_yaml_files(
    dir: &Path,
    recursive: bool,
    files: &mut Vec<PathBuf>,
) -> Result<(), YAMLError> {
    let entries = fs::read_dir(dir).map_err(|e| YAMLError::ParseError {
        line: 0,
        col: 0,
        message: format!("Failed to read directory {}: {}", dir.display(), e),
    })?;

    for entry in entries {
        let entry = entry.map_err(|e| YAMLError::ParseError {
            line: 0,
            col: 0,
            message: format!("Directory entry error: {}", e),
        })?;

        let path = entry.path();

        if path.is_file() {
            // Check if it's a YAML file
            if let Some(ext) = path.extension() {
                let ext_str = ext.to_string_lossy().to_lowercase();
                if ext_str == "yaml" || ext_str == "yml" {
                    files.push(path);
                }
            }
        } else if path.is_dir() && recursive {
            collect_yaml_files(&path, recursive, files)?;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parallel_loading() {
        Python::with_gil(|py| {
            let yamls = vec![
                "doc: 1".to_string(),
                "doc: 2".to_string(),
                "doc: 3".to_string(),
            ];

            let results = safe_load_many(py, yamls).unwrap();
            assert_eq!(results.len(), 3);
        });
    }

    #[test]
    fn test_parallel_loading_preserves_order() {
        Python::with_gil(|py| {
            let yamls = vec![
                "value: first".to_string(),
                "value: second".to_string(),
                "value: third".to_string(),
            ];

            let results = safe_load_many(py, yamls).unwrap();
            assert_eq!(results.len(), 3);

            // Results should be in the same order as input
            use pyo3::types::PyDict;
            let first = results[0].bind(py).downcast::<PyDict>().unwrap();
            let val: String = first
                .get_item("value")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(val, "first");
        });
    }

    #[test]
    fn test_parallel_loading_with_error() {
        Python::with_gil(|py| {
            let yamls = vec![
                "valid: yaml".to_string(),
                "invalid: yaml: :".to_string(), // This is invalid
                "also_valid: yaml".to_string(),
            ];

            let result = safe_load_many(py, yamls);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_parallel_loading_empty_list() {
        Python::with_gil(|py| {
            let yamls: Vec<String> = vec![];

            let results = safe_load_many(py, yamls).unwrap();
            assert_eq!(results.len(), 0);
        });
    }

    #[test]
    fn test_collect_yaml_files_nonexistent() {
        let mut files = Vec::new();
        let result = collect_yaml_files(Path::new("/nonexistent/path"), false, &mut files);
        assert!(result.is_err());
    }

    #[test]
    fn test_parallel_loading_large_batch() {
        Python::with_gil(|py| {
            // Create a batch of 100 YAML strings
            let yamls: Vec<String> = (0..100).map(|i| format!("key_{}: value_{}", i, i)).collect();

            let results = safe_load_many(py, yamls).unwrap();
            assert_eq!(results.len(), 100);
        });
    }

    #[test]
    fn test_unsafe_load_many() {
        Python::with_gil(|py| {
            let yamls = vec![
                "doc: 1".to_string(),
                "doc: 2".to_string(),
                "doc: 3".to_string(),
            ];

            let results = unsafe_load_many(py, yamls).unwrap();
            assert_eq!(results.len(), 3);
        });
    }
}
