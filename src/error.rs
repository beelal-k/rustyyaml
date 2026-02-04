//! Error types for RustyAML
//!
//! Design goals:
//! 1. Rich error messages (show line/column, context)
//! 2. Convert cleanly to Python exceptions
//! 3. Include suggestions for common mistakes

use pyo3::{exceptions::PyValueError, PyErr};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum YAMLError {
    #[error("YAML parse error at line {line}, column {col}: {message}")]
    ParseError {
        line: usize,
        col: usize,
        message: String,
    },

    #[error("Unsafe YAML tag detected: {tag}\nHint: Use unsafe_load() if you trust this file")]
    UnsafeTag { tag: String },

    #[error("Invalid number format: {value}")]
    InvalidNumber { value: String },

    #[error("File not found: {path}")]
    FileNotFound { path: String },

    #[error("UTF-8 decoding error: {message}")]
    DecodingError { message: String },
}

impl YAMLError {
    /// Create a parse error with context
    pub fn parse(line: usize, col: usize, message: String) -> Self {
        YAMLError::ParseError { line, col, message }
    }

    /// Create an unsafe tag error
    pub fn unsafe_tag(tag: String) -> Self {
        YAMLError::UnsafeTag { tag }
    }

    /// Create an invalid number error
    pub fn invalid_number(value: String) -> Self {
        YAMLError::InvalidNumber { value }
    }

    /// Create a parse error with rich context
    ///
    /// Shows the offending line and points to the error location
    pub fn parse_with_context(
        line: usize,
        col: usize,
        message: String,
        yaml_content: &str,
    ) -> Self {
        let context = extract_context(yaml_content, line, col);

        YAMLError::ParseError {
            line,
            col,
            message: format!("{}\n\n{}", message, context),
        }
    }
}

/// Convert our errors to Python exceptions
impl From<YAMLError> for PyErr {
    fn from(err: YAMLError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}

/// Convert serde_yaml errors to our error type
impl From<serde_yaml::Error> for YAMLError {
    fn from(err: serde_yaml::Error) -> YAMLError {
        // Extract location info if available
        if let Some(location) = err.location() {
            YAMLError::ParseError {
                line: location.line(),
                col: location.column(),
                message: format!("{}", err),
            }
        } else {
            YAMLError::ParseError {
                line: 0,
                col: 0,
                message: format!("{}", err),
            }
        }
    }
}

/// Convert IO errors
impl From<std::io::Error> for YAMLError {
    fn from(err: std::io::Error) -> YAMLError {
        if err.kind() == std::io::ErrorKind::NotFound {
            YAMLError::FileNotFound {
                path: "unknown".to_string(),
            }
        } else {
            YAMLError::ParseError {
                line: 0,
                col: 0,
                message: format!("IO error: {}", err),
            }
        }
    }
}

/// Extract a few lines of context around an error
fn extract_context(content: &str, error_line: usize, error_col: usize) -> String {
    let lines: Vec<&str> = content.lines().collect();

    if error_line == 0 || error_line > lines.len() {
        return String::new();
    }

    let mut context = String::new();

    // Show 2 lines before
    let start = error_line.saturating_sub(2);
    for i in start..error_line {
        if i < lines.len() && i > 0 {
            context.push_str(&format!("  {} | {}\n", i, lines[i - 1]));
        }
    }

    // Show the error line with pointer
    if error_line <= lines.len() {
        let line_content = lines[error_line - 1];
        context.push_str(&format!("  {} | {}\n", error_line, line_content));

        // Add pointer
        context.push_str(&format!(
            "  {} | {}^\n",
            " ".repeat(error_line.to_string().len()),
            " ".repeat(error_col.saturating_sub(1))
        ));
    }

    // Show 1 line after
    if error_line < lines.len() {
        context.push_str(&format!("  {} | {}\n", error_line + 1, lines[error_line]));
    }

    context
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_context() {
        let yaml = "line1: value\nline2 missing_colon\nline3: value";
        let context = extract_context(yaml, 2, 7);

        // Should show line 2 with pointer at column 7
        assert!(context.contains("line2"));
        assert!(context.contains("^"));
    }

    #[test]
    fn test_parse_error_display() {
        let err = YAMLError::parse(5, 10, "unexpected token".to_string());
        let msg = err.to_string();
        assert!(msg.contains("line 5"));
        assert!(msg.contains("column 10"));
        assert!(msg.contains("unexpected token"));
    }

    #[test]
    fn test_unsafe_tag_error() {
        let err = YAMLError::unsafe_tag("!!python/object".to_string());
        let msg = err.to_string();
        assert!(msg.contains("!!python/object"));
        assert!(msg.contains("Hint"));
    }
}
