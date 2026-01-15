#!/usr/bin/env python3
"""
Post-processing script for openapi-generator output.

This script fixes import paths and creates necessary __init__.py files
for the generated API client to work properly with the nested package structure.

When to modify this script:
- If the package structure changes
- If additional post-processing steps are needed (e.g., type hint fixes)
- If the openapi-generator output format changes in future versions

The script can be run standalone after generation:
    python3 scripts/post_generate.py

Or it's automatically called by generate_client.sh
"""

import os
import re
from pathlib import Path


def fix_import_paths(gen_dir: str) -> int:
    """
    Fix import paths in all generated Python files.

    The openapi-generator creates a nested package structure but uses incorrect
    import paths. This function recursively fixes all imports to use the correct
    nested path structure.

    Args:
        gen_dir: Path to the generated directory containing Python files

    Returns:
        Number of files that were modified
    """
    files_fixed = 0

    for root, dirs, files in os.walk(gen_dir):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            with open(file_path, "r") as f:
                content = f.read()

            # Fix 'from' imports from incorrect path to correct nested path
            new_content = re.sub(
                r'from arthur_observability_sdk\._generated\.(api|models|exceptions|api_client|api_response|configuration|rest)',
                r'from arthur_observability_sdk._generated.arthur_observability_sdk._generated.\1',
                content
            )

            # Fix 'import' statements
            new_content = re.sub(
                r'import arthur_observability_sdk\._generated\.(api|models|exceptions|api_client|api_response|configuration|rest)',
                r'import arthur_observability_sdk._generated.arthur_observability_sdk._generated.\1',
                new_content
            )

            # Fix 'from arthur_observability_sdk._generated import' statements
            new_content = re.sub(
                r'from arthur_observability_sdk\._generated import (api|models|exceptions|api_client|api_response|configuration|rest)',
                r'from arthur_observability_sdk._generated.arthur_observability_sdk._generated import \1',
                new_content
            )

            # Only write if content changed
            if new_content != content:
                with open(file_path, "w") as f:
                    f.write(new_content)
                files_fixed += 1

    return files_fixed


def create_init_files(base_path: str) -> None:
    """
    Create necessary __init__.py files for proper package structure.

    The generated code needs two __init__.py files to expose the nested
    modules properly:
    1. _generated/__init__.py - Exposes models and api modules
    2. _generated/arthur_observability_sdk/__init__.py - Re-exports from nested _generated

    Args:
        base_path: Base path where the generated code is located
    """
    # Create _generated/__init__.py
    init_generated = """# Generated API client package
# This makes arthur_observability_sdk._generated.models and other submodules accessible
from arthur_observability_sdk._generated.arthur_observability_sdk._generated import models, api

__all__ = ['models', 'api']
"""

    init_path = os.path.join(base_path, "_generated", "__init__.py")
    with open(init_path, "w") as f:
        f.write(init_generated)
    print(f"✓ Created {init_path}")

    # Create _generated/arthur_observability_sdk/__init__.py
    init_nested = """# Re-export the generated module for convenience
from arthur_observability_sdk._generated.arthur_observability_sdk import _generated

# Make models accessible at the top level
models = _generated.models
api = _generated.api
"""

    nested_init_path = os.path.join(base_path, "_generated", "arthur_observability_sdk", "__init__.py")
    with open(nested_init_path, "w") as f:
        f.write(init_nested)
    print(f"✓ Created {nested_init_path}")


def main():
    """Main entry point for post-generation processing."""
    # Determine base path (assuming script is in scripts/ directory)
    script_dir = Path(__file__).parent
    base_path = script_dir.parent / "src" / "arthur_observability_sdk"

    # Fix import paths
    print("Fixing import paths in generated code...")
    gen_dir = base_path / "_generated" / "arthur_observability_sdk" / "_generated"
    files_fixed = fix_import_paths(str(gen_dir))
    print(f"✓ Fixed import paths in {files_fixed} files")

    # Create __init__.py files
    print("Creating package init files...")
    create_init_files(str(base_path))

    print("✓ Post-generation processing complete!")


if __name__ == "__main__":
    main()
