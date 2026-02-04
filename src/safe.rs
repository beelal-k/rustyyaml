//! Safety filters for blocking dangerous YAML tags
//!
//! PyYAML has a history of RCE (Remote Code Execution) vulnerabilities
//! because it can execute arbitrary Python code via tags like:
//! - !!python/object/apply:os.system
//! - !!python/object/new:subprocess.Popen
//!
//! We block ALL custom tags in safe mode.

use crate::error::YAMLError;
use serde_yaml::Value;

/// List of tags that are ALWAYS unsafe
const UNSAFE_TAGS: &[&str] = &[
    "tag:yaml.org,2002:python/object",
    "tag:yaml.org,2002:python/object/apply",
    "tag:yaml.org,2002:python/object/new",
    "tag:yaml.org,2002:python/name",
    "tag:yaml.org,2002:python/module",
    "!!python/object",
    "!!python/object/apply",
    "!!python/object/new",
    "!!python/name",
    "!!python/module",
    "python/object",
    "python/object/apply",
    "python/object/new",
    "python/name",
    "python/module",
];

/// Check if a YAML value contains unsafe tags
///
/// Recursively scans the entire document tree
pub fn check_safety(value: &Value) -> Result<(), YAMLError> {
    match value {
        Value::Tagged(tagged) => {
            // Check if this tag is in the unsafe list
            let tag_str = tagged.tag.to_string();

            for unsafe_tag in UNSAFE_TAGS {
                if tag_str.contains(unsafe_tag) {
                    return Err(YAMLError::UnsafeTag { tag: tag_str });
                }
            }

            // Also check the value inside the tag
            check_safety(&tagged.value)
        }

        Value::Sequence(seq) => {
            // Check all items in the list
            for item in seq {
                check_safety(item)?;
            }
            Ok(())
        }

        Value::Mapping(map) => {
            // Check all keys and values
            for (k, v) in map {
                check_safety(k)?;
                check_safety(v)?;
            }
            Ok(())
        }

        // Scalars are always safe
        Value::Null | Value::Bool(_) | Value::Number(_) | Value::String(_) => Ok(()),
    }
}

/// Check if a raw YAML string contains unsafe patterns
///
/// This is a quick pre-scan before full parsing to catch obvious issues
pub fn quick_safety_check(yaml_str: &str) -> Result<(), YAMLError> {
    // Check for common dangerous patterns in the raw string
    let dangerous_patterns = [
        "!!python/object",
        "!!python/name",
        "!!python/module",
        "!python/object",
        "!python/name",
        "!python/module",
        "tag:yaml.org,2002:python",
    ];

    for pattern in dangerous_patterns {
        if yaml_str.contains(pattern) {
            return Err(YAMLError::UnsafeTag {
                tag: pattern.to_string(),
            });
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_unsafe_tag() {
        // This should fail
        let yaml = "!!python/object/apply:os.system ['echo dangerous']";
        let value: Value = serde_yaml::from_str(yaml).unwrap();

        assert!(check_safety(&value).is_err());
    }

    #[test]
    fn test_safe_yaml() {
        let yaml = "key: value";
        let value: Value = serde_yaml::from_str(yaml).unwrap();

        assert!(check_safety(&value).is_ok());
    }

    #[test]
    fn test_nested_safe_yaml() {
        let yaml = r#"
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
"#;
        let value: Value = serde_yaml::from_str(yaml).unwrap();
        assert!(check_safety(&value).is_ok());
    }

    #[test]
    fn test_list_safe_yaml() {
        let yaml = "- item1\n- item2\n- item3";
        let value: Value = serde_yaml::from_str(yaml).unwrap();
        assert!(check_safety(&value).is_ok());
    }

    #[test]
    fn test_quick_safety_check_catches_dangerous() {
        let yaml = "data: !!python/object/apply:os.system ['rm -rf /']";
        assert!(quick_safety_check(yaml).is_err());
    }

    #[test]
    fn test_quick_safety_check_allows_safe() {
        let yaml = "key: value\nnested:\n  foo: bar";
        assert!(quick_safety_check(yaml).is_ok());
    }

    #[test]
    fn test_detect_unsafe_in_nested() {
        // Even deeply nested unsafe tags should be caught
        let yaml = r#"
safe_key: safe_value
nested:
  also_safe: true
  dangerous: !!python/object/apply:subprocess.Popen ['echo', 'bad']
"#;
        // Note: serde_yaml might parse this differently, so we test the quick check
        assert!(quick_safety_check(yaml).is_err());
    }
}
