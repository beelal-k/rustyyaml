#!/bin/bash
# update_version.sh - Update version across all project files
#
# Usage: ./scripts/update_version.sh 0.2.0

set -e

NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: ./scripts/update_version.sh <version>"
    echo "Example: ./scripts/update_version.sh 0.2.0"
    exit 1
fi

# Validate version format (basic semver check)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    echo "Error: Invalid version format '$NEW_VERSION'"
    echo "Expected format: X.Y.Z or X.Y.Z-suffix (e.g., 0.2.0, 1.0.0-beta.1)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Updating version to $NEW_VERSION..."
echo ""

# Get current versions
CARGO_VERSION=$(grep '^version = ' Cargo.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

echo "Current versions:"
echo "  Cargo.toml:     $CARGO_VERSION"
echo "  pyproject.toml: $PYPROJECT_VERSION"
echo ""

# Update Cargo.toml
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \"$CARGO_VERSION\"/version = \"$NEW_VERSION\"/" Cargo.toml
else
    # Linux
    sed -i "s/^version = \"$CARGO_VERSION\"/version = \"$NEW_VERSION\"/" Cargo.toml
fi

# Update pyproject.toml
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/^version = \"$PYPROJECT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
else
    sed -i "s/^version = \"$PYPROJECT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi

# Verify updates
NEW_CARGO_VERSION=$(grep '^version = ' Cargo.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
NEW_PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

echo "Updated versions:"
echo "  Cargo.toml:     $NEW_CARGO_VERSION"
echo "  pyproject.toml: $NEW_PYPROJECT_VERSION"
echo ""

if [ "$NEW_CARGO_VERSION" = "$NEW_VERSION" ] && [ "$NEW_PYPROJECT_VERSION" = "$NEW_VERSION" ]; then
    echo "✅ Version updated successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: git diff"
    echo "  2. Commit: git add Cargo.toml pyproject.toml && git commit -m 'Bump version to $NEW_VERSION'"
    echo "  3. Tag: git tag v$NEW_VERSION"
    echo "  4. Push: git push origin main --tags"
else
    echo "❌ Error: Version update failed!"
    exit 1
fi
