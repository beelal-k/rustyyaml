"""Basic functionality tests for RustyAML"""

import tempfile
from pathlib import Path

import pytest
import rustyaml as yaml


class TestBasicParsing:
    """Test basic YAML parsing"""

    def test_empty_string(self):
        """Empty string should return None"""
        result = yaml.safe_load("")
        assert result is None

    def test_null_value(self):
        """Null values"""
        result = yaml.safe_load("key: null")
        assert result == {"key": None}

    def test_null_explicit(self):
        """Explicit null"""
        result = yaml.safe_load("null")
        assert result is None

    def test_tilde_null(self):
        """Tilde represents null"""
        result = yaml.safe_load("key: ~")
        assert result == {"key": None}

    def test_boolean_values(self):
        """Boolean parsing (YAML 1.2 spec)"""
        # Note: YAML 1.2 only treats 'true'/'false' as booleans
        # 'yes'/'no' are strings in YAML 1.2 (unlike YAML 1.1)
        result = yaml.safe_load(
            """
        t1: true
        t2: True
        t3: TRUE
        f1: false
        f2: False
        f3: FALSE
        """
        )
        assert result["t1"] is True
        assert result["t2"] is True
        assert result["t3"] is True
        assert result["f1"] is False
        assert result["f2"] is False
        assert result["f3"] is False

    def test_yes_no_are_strings(self):
        """YAML 1.2: yes/no are strings, not booleans"""
        result = yaml.safe_load(
            """
        yes_val: yes
        no_val: no
        """
        )
        # In YAML 1.2, yes/no are strings
        assert result["yes_val"] == "yes"
        assert result["no_val"] == "no"

    def test_integer_values(self):
        """Integer parsing"""
        result = yaml.safe_load(
            """
        decimal: 123
        negative: -456
        zero: 0
        large: 1234567890
        """
        )
        assert result["decimal"] == 123
        assert result["negative"] == -456
        assert result["zero"] == 0
        assert result["large"] == 1234567890

    def test_float_values(self):
        """Float parsing"""
        result = yaml.safe_load(
            """
        simple: 3.14
        negative: -2.5
        scientific: 1.23e-4
        infinity: .inf
        neg_infinity: -.inf
        """
        )
        assert result["simple"] == 3.14
        assert result["negative"] == -2.5
        assert abs(result["scientific"] - 1.23e-4) < 1e-10
        assert result["infinity"] == float("inf")
        assert result["neg_infinity"] == float("-inf")

    def test_nan_value(self):
        """NaN parsing"""
        result = yaml.safe_load("value: .nan")
        import math

        assert math.isnan(result["value"])

    def test_string_values(self):
        """String parsing"""
        result = yaml.safe_load(
            """
        plain: hello world
        quoted: "hello world"
        single: 'hello world'
        """
        )
        assert result["plain"] == "hello world"
        assert result["quoted"] == "hello world"
        assert result["single"] == "hello world"

    def test_multiline_string_literal(self):
        """Literal block scalar (|)"""
        result = yaml.safe_load(
            """
        text: |
          line 1
          line 2
          line 3
        """
        )
        assert "line 1" in result["text"]
        assert "line 2" in result["text"]
        assert "line 3" in result["text"]

    def test_multiline_string_folded(self):
        """Folded block scalar (>)"""
        result = yaml.safe_load(
            """
        text: >
          this is a
          folded string
        """
        )
        assert "this is a" in result["text"]

    def test_list_values(self):
        """List parsing"""
        result = yaml.safe_load(
            """
        - item1
        - item2
        - item3
        """
        )
        assert result == ["item1", "item2", "item3"]

    def test_inline_list(self):
        """Inline list parsing"""
        result = yaml.safe_load("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_nested_dict(self):
        """Nested dictionary"""
        result = yaml.safe_load(
            """
        database:
          host: localhost
          port: 5432
          credentials:
            username: admin
            password: secret
        """
        )
        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 5432
        assert result["database"]["credentials"]["username"] == "admin"
        assert result["database"]["credentials"]["password"] == "secret"

    def test_inline_dict(self):
        """Inline dict parsing"""
        result = yaml.safe_load("{a: 1, b: 2}")
        assert result == {"a": 1, "b": 2}

    def test_mixed_list(self):
        """List with mixed types"""
        result = yaml.safe_load(
            """
        - string
        - 123
        - 3.14
        - true
        - null
        """
        )
        assert result == ["string", 123, 3.14, True, None]

    def test_list_of_dicts(self):
        """List of dictionaries"""
        result = yaml.safe_load(
            """
        - name: Alice
          age: 30
        - name: Bob
          age: 25
        """
        )
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == 30
        assert result[1]["name"] == "Bob"
        assert result[1]["age"] == 25

    def test_dict_with_list_values(self):
        """Dictionary with list values"""
        result = yaml.safe_load(
            """
        fruits:
          - apple
          - banana
          - cherry
        vegetables:
          - carrot
          - potato
        """
        )
        assert result["fruits"] == ["apple", "banana", "cherry"]
        assert result["vegetables"] == ["carrot", "potato"]

    def test_complex_nested_structure(self):
        """Complex nested structure"""
        result = yaml.safe_load(
            """
        company:
          name: Acme Corp
          departments:
            - name: Engineering
              employees:
                - name: Alice
                  skills:
                    - Python
                    - Rust
                - name: Bob
                  skills:
                    - JavaScript
            - name: Marketing
              employees:
                - name: Charlie
                  skills:
                    - SEO
        """
        )
        assert result["company"]["name"] == "Acme Corp"
        assert len(result["company"]["departments"]) == 2
        eng = result["company"]["departments"][0]
        assert eng["name"] == "Engineering"
        assert eng["employees"][0]["name"] == "Alice"
        assert "Python" in eng["employees"][0]["skills"]


class TestMultipleDocuments:
    """Test load_all functionality"""

    def test_multiple_documents(self):
        """Parse multiple YAML documents"""
        docs = yaml.load_all(
            """doc: 1
---
doc: 2
---
doc: 3
"""
        )
        assert len(docs) == 3
        assert docs[0] == {"doc": 1}
        assert docs[1] == {"doc": 2}
        assert docs[2] == {"doc": 3}

    def test_single_document(self):
        """load_all with single document"""
        docs = yaml.load_all("key: value")
        assert len(docs) == 1
        assert docs[0] == {"key": "value"}

    def test_empty_documents(self):
        """Multiple documents with some empty"""
        docs = yaml.load_all(
            """doc: 1
---
---
doc: 3
"""
        )
        assert len(docs) == 3
        assert docs[0] == {"doc": 1}
        assert docs[1] is None
        assert docs[2] == {"doc": 3}

    def test_mixed_type_documents(self):
        """Documents of different types"""
        docs = yaml.load_all(
            """- item1
- item2
---
key: value
---
just a string
"""
        )
        assert len(docs) == 3
        assert docs[0] == ["item1", "item2"]
        assert docs[1] == {"key": "value"}
        assert docs[2] == "just a string"


class TestFileOperations:
    """Test file loading"""

    def test_load_from_path(self, tmp_path):
        """Load from Path object"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")

        result = yaml.safe_load(yaml_file)
        assert result == {"key": "value"}

    def test_load_from_file_object(self, tmp_path):
        """Load from file object"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")

        with open(yaml_file) as f:
            result = yaml.safe_load(f)

        assert result == {"key": "value"}

    def test_load_from_file_object_binary(self, tmp_path):
        """Load from binary file object"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")

        with open(yaml_file, "rb") as f:
            result = yaml.safe_load(f)

        assert result == {"key": "value"}

    def test_load_from_bytes(self):
        """Load from bytes"""
        yaml_bytes = b"key: value"
        result = yaml.safe_load(yaml_bytes)
        assert result == {"key": "value"}

    def test_safe_load_file(self, tmp_path):
        """Test safe_load_file convenience function"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")

        result = yaml.safe_load_file(yaml_file)
        assert result == {"key": "value"}

    def test_load_all_file(self, tmp_path):
        """Test load_all_file convenience function"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("doc: 1\n---\ndoc: 2")

        result = yaml.load_all_file(yaml_file)
        assert len(result) == 2


class TestErrorHandling:
    """Test error cases"""

    def test_invalid_yaml_syntax(self):
        """Invalid YAML syntax"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load("key: : invalid")

    def test_unclosed_bracket(self):
        """Unclosed bracket"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load("[1, 2, 3")

    def test_unclosed_brace(self):
        """Unclosed brace"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load("{a: 1, b: 2")

    def test_invalid_utf8(self):
        """Invalid UTF-8 bytes"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(b"\xff\xfe")

    def test_file_not_found(self):
        """Non-existent file"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(Path("/nonexistent/file.yaml"))

    def test_bad_indentation(self):
        """Inconsistent indentation"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(
                """
key:
  nested1: value1
 nested2: value2
"""
            )

    def test_duplicate_key_allowed(self):
        """Duplicate keys (YAML allows, last wins)"""
        # Note: serde_yaml may reject duplicate keys
        # This test checks either behavior is acceptable
        try:
            result = yaml.safe_load("key: first\nkey: second")
            # If it succeeds, last value should win
            assert result["key"] == "second"
        except yaml.YAMLError:
            # serde_yaml rejects duplicate keys - that's also valid
            pass


class TestSafety:
    """Test security features"""

    def test_reject_python_object(self):
        """Reject !!python/object tag"""
        dangerous_yaml = "!!python/object/apply:os.system ['echo bad']"

        with pytest.raises(yaml.YAMLError) as exc_info:
            yaml.safe_load(dangerous_yaml)

        assert "unsafe" in str(exc_info.value).lower() or "tag" in str(
            exc_info.value
        ).lower()

    def test_reject_python_name(self):
        """Reject !!python/name tag"""
        dangerous_yaml = "!!python/name:os.system"

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(dangerous_yaml)

    def test_reject_python_module(self):
        """Reject !!python/module tag"""
        dangerous_yaml = "!!python/module:os"

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(dangerous_yaml)

    def test_safe_vs_unsafe_basic(self):
        """Both modes work for safe YAML"""
        safe_yaml = "key: value"

        safe_result = yaml.safe_load(safe_yaml)
        unsafe_result = yaml.unsafe_load(safe_yaml)

        assert safe_result == unsafe_result


class TestBatchOperations:
    """Test parallel batch loading"""

    def test_load_many_basic(self):
        """Load multiple YAML strings"""
        yamls = [
            "doc: 1",
            "doc: 2",
            "doc: 3",
        ]

        results = yaml.safe_load_many(yamls)

        assert len(results) == 3
        assert results[0] == {"doc": 1}
        assert results[1] == {"doc": 2}
        assert results[2] == {"doc": 3}

    def test_load_many_empty(self):
        """Load empty list"""
        results = yaml.safe_load_many([])
        assert results == []

    def test_load_many_preserves_order(self):
        """Results should be in same order as input"""
        yamls = [f"index: {i}" for i in range(10)]

        results = yaml.safe_load_many(yamls)

        for i, result in enumerate(results):
            assert result["index"] == i

    def test_load_many_with_error(self):
        """Error in one document fails the batch"""
        yamls = [
            "valid: yaml",
            "invalid: yaml: :",
            "also_valid: yaml",
        ]

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load_many(yamls)

    def test_load_directory(self, tmp_path):
        """Load all YAML files from directory"""
        # Create test files
        (tmp_path / "file1.yaml").write_text("data: 1")
        (tmp_path / "file2.yml").write_text("data: 2")
        (tmp_path / "not_yaml.txt").write_text("ignored")

        results = yaml.load_directory(tmp_path)

        assert len(results) == 2
        filenames = [path for path, _ in results]
        assert any("file1.yaml" in f for f in filenames)
        assert any("file2.yml" in f for f in filenames)

    def test_load_directory_recursive(self, tmp_path):
        """Load YAML files recursively"""
        (tmp_path / "root.yaml").write_text("level: 0")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.yaml").write_text("level: 1")

        # Non-recursive should only get root
        results = yaml.load_directory(tmp_path, recursive=False)
        assert len(results) == 1

        # Recursive should get both
        results = yaml.load_directory(tmp_path, recursive=True)
        assert len(results) == 2

    def test_load_directory_not_found(self):
        """Non-existent directory"""
        with pytest.raises(yaml.YAMLError):
            yaml.load_directory("/nonexistent/path")


class TestPyYAMLCompatibility:
    """Test compatibility with PyYAML API"""

    def test_load_alias(self):
        """load() should work like safe_load()"""
        result = yaml.load("key: value")
        assert result == {"key": "value"}

    def test_yaml_error_is_value_error(self):
        """YAMLError should be a ValueError subclass"""
        assert issubclass(yaml.YAMLError, ValueError)

    def test_version_exists(self):
        """__version__ should be defined"""
        assert hasattr(yaml, "__version__")
        assert isinstance(yaml.__version__, str)
        assert len(yaml.__version__) > 0


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_unicode_content(self):
        """Unicode content handling"""
        result = yaml.safe_load("greeting: 你好世界")
        assert result == {"greeting": "你好世界"}

    def test_emoji_content(self):
        """Emoji content handling"""
        result = yaml.safe_load("emoji: 🦀🐍")
        assert result == {"emoji": "🦀🐍"}

    def test_special_characters_in_strings(self):
        """Special characters in quoted strings"""
        result = yaml.safe_load('key: "value with: colon"')
        assert result == {"key": "value with: colon"}

    def test_numeric_keys(self):
        """Numeric keys in mapping"""
        result = yaml.safe_load("1: one\n2: two")
        assert result[1] == "one"
        assert result[2] == "two"

    def test_boolean_keys(self):
        """Boolean keys in mapping"""
        result = yaml.safe_load("true: yes_value\nfalse: no_value")
        assert result[True] == "yes_value"
        assert result[False] == "no_value"

    def test_anchor_and_alias(self):
        """YAML anchors and aliases (basic)"""
        # Test basic anchor/alias without merge keys
        result = yaml.safe_load(
            """defaults: &defaults
  adapter: postgres
  host: localhost

development:
  inherited: *defaults
  database: dev_db
"""
        )
        assert result["defaults"]["adapter"] == "postgres"
        assert result["development"]["inherited"]["adapter"] == "postgres"
        assert result["development"]["database"] == "dev_db"

    def test_very_long_string(self):
        """Very long string handling"""
        long_string = "x" * 10000
        result = yaml.safe_load(f"key: {long_string}")
        assert result["key"] == long_string

    def test_deeply_nested_structure(self):
        """Deeply nested structure"""
        yaml_str = "level0:\n"
        for i in range(1, 20):
            yaml_str += "  " * i + f"level{i}:\n"
        yaml_str += "  " * 20 + "value: deep"

        result = yaml.safe_load(yaml_str)
        current = result
        for i in range(20):
            current = current[f"level{i}"]
        assert current["value"] == "deep"

    def test_large_list(self):
        """Large list handling"""
        items = [f"item{i}" for i in range(1000)]
        yaml_str = "\n".join(f"- {item}" for item in items)

        result = yaml.safe_load(yaml_str)
        assert len(result) == 1000
        assert result[0] == "item0"
        assert result[999] == "item999"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
