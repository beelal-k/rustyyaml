# Publishing RustyYAML to PyPI

This guide covers how to publish RustyYAML so users can install it with `pip install rustyyaml`.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [One-Time Setup](#one-time-setup)
3. [Publishing Methods](#publishing-methods)
   - [Method 1: Automated via GitHub Actions (Recommended)](#method-1-automated-via-github-actions-recommended)
   - [Method 2: Manual Publishing](#method-2-manual-publishing)
4. [Pre-Release Checklist](#pre-release-checklist)
5. [Versioning](#versioning)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Accounts Required

1. **PyPI Account**: Create at https://pypi.org/account/register/
2. **TestPyPI Account** (recommended): Create at https://test.pypi.org/account/register/
3. **GitHub Account**: For automated releases

### Tools Required

```bash
# Install maturin (the build tool for Rust+Python)
pip install maturin twine

# Ensure Rust is installed
rustup --version
```

---

## One-Time Setup

### Step 1: Update Project Metadata

Edit `Cargo.toml` and `pyproject.toml` with your actual information:

```toml
# Cargo.toml
[package]
name = "rustyyaml"
version = "0.1.0"
authors = ["Your Real Name <your.email@example.com>"]
repository = "https://github.com/YOUR_USERNAME/rustyyaml"
```

```toml
# pyproject.toml
[project]
authors = [
    {name = "Your Real Name", email = "your.email@example.com"}
]

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/rustyyaml"
Repository = "https://github.com/YOUR_USERNAME/rustyyaml"
```

### Step 2: Check Package Name Availability

Before publishing, verify "rustyyaml" is available on PyPI:

```bash
pip index versions rustyyaml
```

If the name is taken, you'll need to choose a different name.

### Step 3: Set Up PyPI API Token

#### For Manual Publishing:

1. Go to https://pypi.org/manage/account/token/
2. Create a new API token with scope "Entire account" (or project-specific after first upload)
3. Save the token securely (starts with `pypi-`)

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

#### For GitHub Actions (Trusted Publishing - Recommended):

1. Go to your PyPI account → Publishing
2. Add a new "pending publisher":
   - PyPI Project Name: `rustyyaml`
   - Owner: `YOUR_GITHUB_USERNAME`
   - Repository: `rustyyaml`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

This allows GitHub Actions to publish without storing API tokens.

### Step 4: Create GitHub Repository

```bash
cd rustyyaml
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/rustyyaml.git
git push -u origin main
```

### Step 5: Set Up GitHub Environment

1. Go to Repository → Settings → Environments
2. Create an environment named `pypi`
3. (Optional) Add protection rules like required reviewers

---

## Publishing Methods

### Method 1: Automated via GitHub Actions (Recommended)

This is the easiest and most reliable method. The workflow in `.github/workflows/release.yml` automatically:

- Builds wheels for all platforms (Linux, macOS, Windows)
- Builds for all Python versions (3.8-3.12)
- Cross-compiles for ARM (aarch64, armv7)
- Builds macOS universal binaries (Intel + Apple Silicon)
- Publishes to PyPI
- Creates a GitHub Release

#### To Release:

```bash
# 1. Update version in both files
#    - Cargo.toml: version = "0.2.0"
#    - pyproject.toml: version = "0.2.0"

# 2. Update CHANGELOG.md (if you have one)

# 3. Commit the version bump
git add Cargo.toml pyproject.toml
git commit -m "Bump version to 0.2.0"

# 4. Create and push a version tag
git tag v0.2.0
git push origin main --tags
```

The GitHub Action will trigger automatically and publish to PyPI within ~10-15 minutes.

#### Monitor the Release:

1. Go to Repository → Actions
2. Watch the "Release" workflow
3. Once complete, verify at https://pypi.org/project/rustyyaml/

### Method 2: Manual Publishing

For quick releases or when GitHub Actions aren't available.

#### Step 1: Build Wheels Locally

```bash
cd rustyaml

# Activate virtual environment
source .venv/bin/activate

# Build a wheel for your current platform
maturin build --release

# Wheels are placed in target/wheels/
ls target/wheels/
```

#### Step 2: Test on TestPyPI First (Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi target/wheels/*.whl

# Test installation
pip install --index-url https://test.pypi.org/simple/ rustyyaml
python -c "import rustyyaml; print(rustyyaml.safe_load('key: value'))"
```

#### Step 3: Publish to PyPI

```bash
# Upload to real PyPI
twine upload target/wheels/*.whl

# Or use maturin directly
maturin publish
```

#### Building for Multiple Platforms

For a proper release, you need wheels for all platforms. Options:

**Option A: Use Docker for Linux wheels (manylinux)**

```bash
# Build manylinux wheels using Docker
docker run --rm -v $(pwd):/io ghcr.io/pyo3/maturin build --release -i python3.10 python3.11 python3.12
```

**Option B: Use cross-compilation**

```bash
# Install cross-compilation targets
rustup target add x86_64-unknown-linux-gnu
rustup target add aarch64-unknown-linux-gnu

# Build for specific target
maturin build --release --target x86_64-unknown-linux-gnu
```

**Option C: Use CI/CD (GitHub Actions)**

This is why the automated method is recommended—it handles all platforms automatically.

---

## Pre-Release Checklist

Before every release:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Benchmarks look good: `python benchmarks/quick_benchmark.py`
- [ ] No compiler warnings: `cargo build --release 2>&1 | grep -i warning`
- [ ] Documentation is updated: `README.md`
- [ ] Version bumped in both files:
  - [ ] `Cargo.toml`
  - [ ] `pyproject.toml`
- [ ] CHANGELOG updated (if maintaining one)
- [ ] License files present: `LICENSE-MIT`, `LICENSE-APACHE`
- [ ] Git working directory is clean: `git status`

### Quick Verification Script

```bash
#!/bin/bash
echo "=== Pre-Release Checks ==="

echo -n "Cargo.toml version: "
grep '^version' Cargo.toml | head -1

echo -n "pyproject.toml version: "
grep '^version' pyproject.toml | head -1

echo ""
echo "Running tests..."
pytest tests/ -q

echo ""
echo "Running quick benchmark..."
python benchmarks/quick_benchmark.py 2>&1 | tail -20

echo ""
echo "Checking for uncommitted changes..."
git status --short
```

---

## Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking API changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, backward compatible

### Pre-release Versions

```
0.1.0-alpha.1  # Alpha release
0.1.0-beta.1   # Beta release  
0.1.0-rc.1     # Release candidate
0.1.0          # Stable release
```

### Version Sync Script

Create this script to keep versions in sync:

```bash
#!/bin/bash
# update_version.sh

NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: ./update_version.sh 0.2.0"
    exit 1
fi

# Update Cargo.toml
sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" Cargo.toml

# Update pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

echo "Updated version to $NEW_VERSION"
grep "^version" Cargo.toml pyproject.toml
```

---

## Troubleshooting

### "Package name already exists"

The name `rustyyaml` might be taken. Check and choose an alternative:

```bash
pip index versions rustyyaml
# If taken, try: rustyyaml-py, rusty-yaml, etc.
```

### "Invalid wheel filename"

Ensure maturin is building correctly:

```bash
maturin build --release -v
```

### "Authentication failed"

Check your `~/.pypirc` or use environment variables:

```bash
export MATURIN_PYPI_TOKEN=pypi-your-token-here
maturin publish
```

### "Wheel platform mismatch"

You're trying to upload a wheel built for a different platform. Use GitHub Actions for multi-platform builds, or build inside Docker:

```bash
docker run --rm -v $(pwd):/io ghcr.io/pyo3/maturin build --release
```

### GitHub Actions Failing

1. Check the Actions tab for error logs
2. Verify the `pypi` environment exists in Settings → Environments
3. Ensure trusted publishing is configured on PyPI
4. Check that tag format matches: `v*` (e.g., `v0.1.0`)

### "Module not found" After Installation

The installed package structure might be wrong. Verify:

```bash
pip show -f rustyaml
python -c "import rustyaml; print(dir(rustyaml))"
```

---

## Quick Reference

### Release Commands

```bash
# Bump version
./update_version.sh 0.2.0

# Commit and tag
git add -A
git commit -m "Release v0.2.0"
git tag v0.2.0
git push origin main --tags

# Manual release (single platform)
maturin build --release
twine upload target/wheels/*.whl
```

### Useful Links

- **PyPI Project**: https://pypi.org/project/rustyyaml/
- **TestPyPI Project**: https://test.pypi.org/project/rustyyaml/
- **Maturin Documentation**: https://www.maturin.rs/
- **PyO3 User Guide**: https://pyo3.rs/
- **GitHub Actions for Python**: https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

---

## After Publishing

Once published, users can install with:

```bash
pip install rustyyaml
```

Verify the release:

```bash
pip install rustyyaml
python -c "import rustyyaml; print(rustyyaml.safe_load('hello: world'))"
# Output: {'hello': 'world'}
```

Congratulations! 🎉 Your Rust-powered Python package is now available to the world!