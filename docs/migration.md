# Migration Guide: PyYAML → RustyAML

This guide helps you migrate from PyYAML to RustyAML with minimal code changes.

## Table of Contents

1. [Installation](#installation)
2. [Quick Migration](#quick-migration)
3. [API Compatibility](#api-compatibility)
4. [Breaking Changes](#breaking-changes)
5. [Migration Strategies](#migration-strategies)
6. [Common Issues](#common-issues)
7. [Performance Tips](#performance-tips)

---

## Installation

```bash
# Install RustyAML
pip install rustyaml

# Optional: Keep PyYAML for dump operations (not yet supported in RustyAML)
pip install pyyaml
```

## Quick Migration

### One-Line Migration

Add this to the top of your main file:

```python
import rustyaml.compat  # Must be first!
import yaml  # This now uses RustyAML

# All your existing code works unchanged
config = yaml.safe_load(open('config.yaml'))
```

### Simple Import Replacement

```python
# Before
import yaml

# After
import rustyaml as yaml

# Your code works the same
data = yaml.safe_load("key: value")
```

---

## API Compatibility

### ✅ Fully Compatible (Drop-in Replacement)

| PyYAML | RustyAML | Notes |
|--------|----------|-------|
| `yaml.safe_load(stream)` | `rustyaml.safe_load(stream)` | 100% compatible |
| `yaml.load(stream, Loader)` | `rustyaml.load(stream)` | Defaults to safe mode |
| `yaml.load_all(stream, Loader)` | `rustyaml.load_all(stream)` | Returns list, not iterator |
| `yaml.YAMLError` | `rustyaml.YAMLError` | Same exception handling |

### ⚠️ Behavioral Differences

| Feature | PyYAML | RustyAML |
|---------|--------|----------|
| `load()` default | Unsafe (requires Loader) | Safe by default |
| `load_all()` return | Generator/iterator | List |
| Custom tags | Allowed with loaders | Blocked in safe mode |
| `!!python/object` | Executes code | Raises error |

### ❌ Not Yet Supported

| PyYAML Function | Status | Alternative |
|-----------------|--------|-------------|
| `yaml.dump()` | Coming in v2.0 | Use PyYAML |
| `yaml.safe_dump()` | Coming in v2.0 | Use PyYAML |
| `yaml.dump_all()` | Coming in v2.0 | Use PyYAML |
| `yaml.add_constructor()` | Not planned | Use plain Python objects |
| `yaml.add_representer()` | Not planned | Use PyYAML |
| `yaml.YAMLObject` | Not supported | Use dictionaries |
| Custom Loaders | Not supported | Use safe_load/unsafe_load |

---

## Breaking Changes

### 1. Default Safety Mode

**PyYAML (before Python 3.9):**
```python
# DANGEROUS - could execute arbitrary code!
yaml.load(untrusted_input)
```

**RustyAML:**
```python
# SAFE - equivalent to safe_load()
yaml.load(untrusted_input)  # No code execution possible
```

### 2. load_all() Returns List

**PyYAML:**
```python
# Returns a generator
for doc in yaml.load_all(stream, Loader=SafeLoader):
    process(doc)
```

**RustyAML:**
```python
# Returns a list
docs = yaml.load_all(stream)
for doc in docs:
    process(doc)

# Or use list directly
first_doc = yaml.load_all(stream)[0]
```

### 3. Custom Python Objects Rejected

**PyYAML:**
```python
# Would instantiate a Python object
yaml.load("!!python/object:mymodule.MyClass {}", Loader=UnsafeLoader)
```

**RustyAML:**
```python
# Raises YAMLError: Unsafe tag detected
yaml.safe_load("!!python/object:mymodule.MyClass {}")

# Use unsafe_load if you trust the source
yaml.unsafe_load("!!python/object:mymodule.MyClass {}")  # Still may not work for all tags
```

### 4. Loader Parameter Ignored

**PyYAML:**
```python
yaml.load(stream, Loader=yaml.FullLoader)
yaml.load(stream, Loader=yaml.UnsafeLoader)
```

**RustyAML:**
```python
# Loader parameter is ignored - use the appropriate function
yaml.safe_load(stream)    # Safe mode (default)
yaml.unsafe_load(stream)  # Unsafe mode
```

---

## Migration Strategies

### Strategy 1: Simple Replace (Recommended)

Best for: New projects or projects using only `safe_load()`.

```python
# Replace all occurrences
# Before:
import yaml

# After:
import rustyaml as yaml
```

### Strategy 2: Compatibility Layer

Best for: Large codebases with many `import yaml` statements.

```python
# In your __init__.py or main entry point
import rustyaml.compat

# All subsequent `import yaml` uses RustyAML
```

### Strategy 3: Gradual Migration

Best for: Projects that need both loading and dumping.

```python
# Use RustyAML for loading (fast)
import rustyaml

# Keep PyYAML for dumping (not yet in RustyAML)
import yaml as pyyaml

# Loading - use RustyAML
config = rustyaml.safe_load(open('config.yaml'))

# Dumping - use PyYAML
output = pyyaml.dump(data)
```

### Strategy 4: Wrapper Module

Best for: Maximum control and gradual rollout.

```python
# myproject/yaml_wrapper.py
try:
    import rustyaml as _yaml
    USING_RUSTYAML = True
except ImportError:
    import yaml as _yaml
    USING_RUSTYAML = False

def safe_load(stream):
    return _yaml.safe_load(stream)

def load_all(stream):
    result = _yaml.load_all(stream)
    # Ensure consistent return type
    return list(result) if not isinstance(result, list) else result

def dump(data, stream=None, **kwargs):
    if USING_RUSTYAML:
        # Fall back to PyYAML for dump
        import yaml
        return yaml.dump(data, stream, **kwargs)
    return _yaml.dump(data, stream, **kwargs)
```

---

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'rustyaml'"

**Solution:**
```bash
pip install rustyaml
```

### Issue: "YAMLError: Unsafe tag detected"

**Cause:** Your YAML contains custom tags like `!!python/object`.

**Solution:**
```python
# If you trust the source:
data = rustyaml.unsafe_load(yaml_string)

# Better: Convert your YAML to use plain data types
# Instead of: !!python/object:myapp.Config {host: localhost}
# Use: {host: localhost}
```

### Issue: "NotImplementedError: dump() is not yet implemented"

**Solution:** Use PyYAML for dumping:
```python
import rustyaml  # For loading
import yaml      # For dumping

config = rustyaml.safe_load(open('config.yaml'))
# ... modify config ...
yaml.dump(config, open('config.yaml', 'w'))
```

### Issue: "TypeError: 'generator' object is not subscriptable"

**Cause:** You're treating `load_all()` result as a generator.

**PyYAML behavior:**
```python
docs = yaml.load_all(stream, Loader=SafeLoader)
first = next(docs)  # Generator iteration
```

**RustyAML behavior:**
```python
docs = rustyaml.load_all(stream)
first = docs[0]  # List indexing
```

### Issue: Performance not improved

**Possible causes:**

1. **Using PyYAML by mistake:**
   ```python
   # Check which library you're using
   import rustyaml
   print(rustyaml.__version__)  # Should print version
   ```

2. **I/O bound, not CPU bound:**
   ```python
   # If reading many files, use batch loading
   configs = rustyaml.load_directory('./configs')
   ```

3. **Debug build:**
   ```bash
   # Ensure you're using release build
   pip install rustyaml --force-reinstall
   ```

---

## Performance Tips

### 1. Use Batch Loading for Multiple Files

```python
# Slow (sequential)
configs = []
for path in paths:
    with open(path) as f:
        configs.append(yaml.safe_load(f))

# Fast (parallel)
yaml_strings = [open(p).read() for p in paths]
configs = rustyaml.safe_load_many(yaml_strings)
```

### 2. Use Directory Loading

```python
# Load all YAML files from a directory
results = rustyaml.load_directory('./configs', recursive=True)
for filepath, data in results:
    print(f"Loaded {filepath}")
```

### 3. Read Files in Batches

```python
# Good for CI/CD pipelines with many config files
import glob

yaml_files = glob.glob('**/*.yaml', recursive=True)
contents = [open(f).read() for f in yaml_files]
parsed = rustyaml.safe_load_many(contents)
```

### 4. Avoid Repeated Parsing

```python
# Bad - parsing same content multiple times
for _ in range(100):
    config = yaml.safe_load(yaml_string)

# Good - parse once, reuse
config = yaml.safe_load(yaml_string)
for _ in range(100):
    use_config(config)
```

---

## Verification Checklist

After migration, verify:

- [ ] All imports updated or compat layer installed
- [ ] `safe_load()` works for your use cases
- [ ] `load_all()` handling updated for list return type
- [ ] Error handling still works with `YAMLError`
- [ ] Tests pass with new library
- [ ] Performance improved (run benchmarks)
- [ ] If using `dump()`, PyYAML fallback in place

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/yourusername/rustyaml/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/rustyaml/discussions)
- **API Reference:** See [README.md](../README.md)