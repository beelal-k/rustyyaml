#!/bin/bash
# RustyAML Release Helper Script
# Usage: ./scripts/release.sh [version]
# Example: ./scripts/release.sh 0.2.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

get_current_version() {
    grep '^version = ' Cargo.toml | head -1 | sed 's/version = "\(.*\)"/\1/'
}

update_version() {
    local new_version=$1

    # Update Cargo.toml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" Cargo.toml
        sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    else
        sed -i "s/^version = \".*\"/version = \"$new_version\"/" Cargo.toml
        sed -i "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    fi
}

check_clean_workdir() {
    if [ -n "$(git status --porcelain)" ]; then
        return 1
    fi
    return 0
}

run_tests() {
    print_header "Running Tests"

    # Check if venv exists and activate
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    # Run Python tests
    if command -v pytest &> /dev/null; then
        pytest tests/ -q || return 1
        print_success "Python tests passed"
    else
        print_warning "pytest not found, skipping Python tests"
    fi

    # Run Cargo tests
    if command -v cargo &> /dev/null; then
        cargo test --quiet || return 1
        print_success "Cargo tests passed"
    fi

    return 0
}

run_checks() {
    print_header "Running Pre-Release Checks"

    # Check required files
    local required_files=("Cargo.toml" "pyproject.toml" "README.md" "LICENSE-MIT" "LICENSE-APACHE")
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "Found $file"
        else
            print_error "Missing $file"
            return 1
        fi
    done

    # Check version sync
    local cargo_version=$(grep '^version = ' Cargo.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
    local pyproject_version=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

    if [ "$cargo_version" == "$pyproject_version" ]; then
        print_success "Versions in sync: $cargo_version"
    else
        print_error "Version mismatch: Cargo.toml=$cargo_version, pyproject.toml=$pyproject_version"
        return 1
    fi

    return 0
}

show_help() {
    echo "RustyAML Release Helper"
    echo ""
    echo "Usage: $0 [command] [version]"
    echo ""
    echo "Commands:"
    echo "  release <version>   Create a new release (e.g., release 0.2.0)"
    echo "  check               Run pre-release checks without releasing"
    echo "  version             Show current version"
    echo "  bump-patch          Bump patch version (0.1.0 -> 0.1.1)"
    echo "  bump-minor          Bump minor version (0.1.0 -> 0.2.0)"
    echo "  bump-major          Bump major version (0.1.0 -> 1.0.0)"
    echo "  help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 release 0.2.0    # Release version 0.2.0"
    echo "  $0 bump-patch       # Bump to next patch version"
    echo "  $0 check            # Run checks only"
}

bump_version() {
    local current=$(get_current_version)
    local major=$(echo $current | cut -d. -f1)
    local minor=$(echo $current | cut -d. -f2)
    local patch=$(echo $current | cut -d. -f3 | cut -d- -f1)

    case $1 in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "$major.$((minor + 1)).0"
            ;;
        patch)
            echo "$major.$minor.$((patch + 1))"
            ;;
    esac
}

do_release() {
    local new_version=$1

    print_header "RustyAML Release v$new_version"

    # Validate version format
    if ! [[ $new_version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        print_error "Invalid version format: $new_version"
        echo "Expected format: X.Y.Z or X.Y.Z-alpha.N"
        exit 1
    fi

    # Check for clean working directory
    if ! check_clean_workdir; then
        print_warning "Working directory has uncommitted changes"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Run checks
    if ! run_checks; then
        print_error "Pre-release checks failed"
        exit 1
    fi

    # Run tests
    if ! run_tests; then
        print_error "Tests failed"
        exit 1
    fi

    # Update version
    print_header "Updating Version to $new_version"
    local old_version=$(get_current_version)
    update_version "$new_version"
    print_success "Updated version: $old_version -> $new_version"

    # Show diff
    echo ""
    echo "Changes:"
    git diff --color Cargo.toml pyproject.toml
    echo ""

    # Confirm
    read -p "Commit, tag, and push? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Aborting. Reverting version changes..."
        git checkout Cargo.toml pyproject.toml
        exit 1
    fi

    # Commit
    git add Cargo.toml pyproject.toml
    git commit -m "Release v$new_version"
    print_success "Created commit"

    # Tag
    git tag "v$new_version"
    print_success "Created tag v$new_version"

    # Push
    echo ""
    read -p "Push to origin? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main --tags
        print_success "Pushed to origin"

        echo ""
        print_header "Release Initiated!"
        echo ""
        echo "GitHub Actions will now:"
        echo "  1. Build wheels for all platforms"
        echo "  2. Publish to PyPI"
        echo "  3. Create a GitHub Release"
        echo ""
        echo "Monitor progress at:"
        echo "  https://github.com/YOUR_USERNAME/rustyaml/actions"
        echo ""
        echo "Once complete, users can install with:"
        echo "  pip install rustyaml==$new_version"
    else
        print_warning "Tag created locally but not pushed"
        echo "To push later: git push origin main --tags"
    fi
}

# Main
case "${1:-help}" in
    release)
        if [ -z "$2" ]; then
            print_error "Version required"
            echo "Usage: $0 release <version>"
            exit 1
        fi
        do_release "$2"
        ;;
    check)
        run_checks
        run_tests
        print_success "All checks passed!"
        ;;
    version)
        echo "Current version: $(get_current_version)"
        ;;
    bump-patch)
        new_ver=$(bump_version patch)
        echo "Bumping to $new_ver"
        do_release "$new_ver"
        ;;
    bump-minor)
        new_ver=$(bump_version minor)
        echo "Bumping to $new_ver"
        do_release "$new_ver"
        ;;
    bump-major)
        new_ver=$(bump_version major)
        echo "Bumping to $new_ver"
        do_release "$new_ver"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
