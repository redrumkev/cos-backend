#!/usr/bin/env python3
"""Module Generator for COS.

Creates new modules by cloning the cc gold standard template with proper
name substitution and configuration updates.
"""

import argparse
import re
import sys
from pathlib import Path

from rich.console import Console

# Initialize rich console for colored output
console = Console()


def _validate_name(name: str, name_type: str) -> None:
    """Validate domain or module name format.

    Args:
    ----
        name: The name to validate
        name_type: Type of name (domain/module) for error messages

    Raises:
    ------
        ValueError: If name format is invalid

    """
    if not name:
        raise ValueError(f"{name_type} name cannot be empty")

    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise ValueError(
            f"{name_type} name must start with lowercase letter and contain only "
            "lowercase letters, numbers, and underscores"
        )


def _copy_template(source_dir: Path, target_dir: Path, module_name: str, domain: str) -> None:
    """Copy and transform template files from cc to new module.

    Args:
    ----
        source_dir: Source cc directory
        target_dir: Target module directory
        module_name: New module name
        domain: Domain name

    Raises:
    ------
        RuntimeError: If file operations fail

    """
    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy each Python file with name transformation
        for source_file in source_dir.glob("*.py"):
            content = source_file.read_text(encoding="utf-8")

            # Replace cc patterns with new module name
            content = content.replace("cc", module_name)
            content = content.replace("CC", module_name.upper())
            content = content.replace("tech_cc", f"{domain}_{module_name}")
            content = content.replace("Control Center", f"{module_name.title()} Module")
            content = content.replace("Central coordination module", f"{module_name} module")

            # Handle main file name transformation
            if source_file.name == "cc_main.py":
                target_file = target_dir / f"{module_name}_main.py"
            else:
                target_file = target_dir / source_file.name

            target_file.write_text(content, encoding="utf-8")

        # Copy YAML files
        for source_file in source_dir.glob("*.yaml"):
            content = source_file.read_text(encoding="utf-8")
            content = content.replace("cc", module_name)
            content = content.replace("tech_cc", f"{domain}_{module_name}")
            target_file = target_dir / source_file.name.replace("cc_", f"{module_name}_")
            target_file.write_text(content, encoding="utf-8")

        console.print(f"✅ Copied template files to {target_dir}", style="green")

    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Failed to copy template files: {e}") from e


def _copy_test_template(source_test_dir: Path, target_test_dir: Path, module_name: str) -> None:
    """Copy and transform test files from cc tests to new module tests.

    Args:
    ----
        source_test_dir: Source cc test directory
        target_test_dir: Target module test directory
        module_name: New module name

    Raises:
    ------
        RuntimeError: If test file operations fail

    """
    try:
        target_test_dir.mkdir(parents=True, exist_ok=True)

        # Create __init__.py
        (target_test_dir / "__init__.py").touch()

        # Copy and transform test files
        for test_file in source_test_dir.glob("test_*.py"):
            content = test_file.read_text(encoding="utf-8")

            # Replace cc with new module name in imports and content
            content = content.replace("from src.backend.cc", f"from src.backend.{module_name}")
            content = content.replace("cc.", f"{module_name}.")
            content = content.replace('"cc"', f'"{module_name}"')
            content = content.replace("'cc'", f"'{module_name}'")
            content = content.replace("cc_", f"{module_name}_")

            target_file = target_test_dir / test_file.name
            target_file.write_text(content, encoding="utf-8")

        console.print(f"✅ Copied test files to {target_test_dir}", style="green")

    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Failed to copy test files: {e}") from e


def _patch_alembic(module_name: str, domain: str) -> None:
    """Update alembic env.py to include new module schemas.

    Args:
    ----
        module_name: New module name
        domain: Domain name

    Raises:
    ------
        RuntimeError: If alembic patch fails

    """
    alembic_env = Path("src/db/migrations/env.py")

    if not alembic_env.exists():
        console.print("⚠️ Alembic env.py not found, skipping patch", style="yellow")
        return

    try:
        content = alembic_env.read_text(encoding="utf-8")

        # Add import for new module models
        import_line = f"from src.backend.{module_name} import models as {module_name}_models  # noqa: F401"
        mem0_import_line = f"from src.backend.{module_name} import mem0_models as {module_name}_mem0_models"

        if import_line not in content:
            # Find the imports section and add new imports
            cc_import_match = re.search(r"from src\.backend\.cc import models as cc_models", content)
            if cc_import_match:
                insert_pos = cc_import_match.end()
                content = content[:insert_pos] + f"\n{import_line}\n{mem0_import_line}" + content[insert_pos:]

            # Update WATCH_SCHEMAS set
            schema_pattern = r"WATCH_SCHEMAS\s*=\s*\{([^}]+)\}"
            schema_match = re.search(schema_pattern, content)
            if schema_match:
                current_schemas = schema_match.group(1)
                if f'"{module_name}"' not in current_schemas:
                    new_schemas = current_schemas.rstrip() + f', "{module_name}", "mem0_{module_name}"'
                    content = content.replace(schema_match.group(0), f"WATCH_SCHEMAS = {{{new_schemas}}}")

            alembic_env.write_text(content, encoding="utf-8")
            console.print("✅ Updated alembic env.py", style="green")
        else:
            console.print("⚠️ Module already exists in alembic env.py", style="yellow")

    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Failed to patch alembic env.py: {e}") from e


def _update_registry(module_name: str, domain: str) -> None:
    """Update Neo4j registry to include new module label.

    Args:
    ----
        module_name: New module name
        domain: Domain name

    Raises:
    ------
        RuntimeError: If registry update fails

    """
    registry_file = Path("src/graph/registry.py")

    if not registry_file.exists():
        console.print("⚠️ Graph registry not found, skipping update", style="yellow")
        return

    try:
        content = registry_file.read_text(encoding="utf-8")

        # Add new module to ModuleLabel enum
        enum_value = f'{module_name.upper()} = "{domain}_{module_name}"'

        if enum_value not in content:
            # Find the ModuleLabel enum and add new entry
            enum_pattern = r"(class ModuleLabel\(str, Enum\):\s*[^#]*?)(    # Future modules)"
            enum_match = re.search(enum_pattern, content, re.DOTALL)

            if enum_match:
                enum_content = enum_match.group(1)
                new_enum = enum_content.rstrip() + f"\n    {enum_value}\n    "
                content = content.replace(enum_match.group(1), new_enum)

                registry_file.write_text(content, encoding="utf-8")
                console.print("✅ Updated graph registry", style="green")
            else:
                console.print("⚠️ Could not find ModuleLabel enum pattern", style="yellow")
        else:
            console.print("⚠️ Module already exists in registry", style="yellow")

    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Failed to update registry: {e}") from e


def generate_module(domain: str, module_name: str, dry_run: bool = False) -> None:
    """Generate a new module based on the cc template.

    Args:
    ----
        domain: Domain name (e.g., tech, zk, publishing)
        module_name: Module name (e.g., pem, auth)
        dry_run: If True, show actions without writing files

    Raises:
    ------
        SystemExit: If validation fails or target already exists
        RuntimeError: If file operations fail

    """
    try:
        # Validate inputs
        _validate_name(domain, "Domain")
        _validate_name(module_name, "Module")

        # Define paths
        src_dir = Path("src")
        backend_dir = src_dir / "backend"
        cc_dir = backend_dir / "cc"
        target_dir = backend_dir / module_name

        # Check if cc template exists
        if not cc_dir.exists():
            console.print("❌ CC template directory not found", style="red")
            sys.exit(1)

        # Check if target already exists
        if target_dir.exists():
            console.print(f"❌ Module {module_name} already exists", style="red")
            sys.exit(1)

        if dry_run:
            console.print(f"🔍 DRY RUN: Would generate module {domain}_{module_name}", style="blue")
            console.print(f"  - Copy from: {cc_dir}")
            console.print(f"  - Copy to: {target_dir}")
            console.print("  - Update alembic env.py")
            console.print("  - Update graph registry")
            console.print(f"  - Create test files in tests/backend/{module_name}/")
            return

        console.print(f"🚀 Generating module {domain}_{module_name}...", style="blue")

        # Copy module files
        _copy_template(cc_dir, target_dir, module_name, domain)

        # Copy test files
        cc_test_dir = Path("tests/backend/cc")
        target_test_dir = Path("tests/backend") / module_name
        if cc_test_dir.exists():
            _copy_test_template(cc_test_dir, target_test_dir, module_name)

        # Update configuration files
        _patch_alembic(module_name, domain)
        _update_registry(module_name, domain)

        console.print(f"✅ Successfully generated module {domain}_{module_name}", style="green")
        console.print("\n📋 Next steps:", style="bold")
        console.print(f"1. Review generated files in src/backend/{module_name}/")
        console.print(f"2. Run: alembic revision --autogenerate -m 'create {module_name} schema tables'")
        console.print("3. Review and apply the migration with: alembic upgrade head")
        console.print(f"4. Run tests: pytest tests/backend/{module_name}/")

    except ValueError as e:
        console.print(f"❌ Validation error: {e}", style="red")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"❌ Generation failed: {e}", style="red")
        sys.exit(1)


def main() -> None:
    """Run the module generator CLI."""
    parser = argparse.ArgumentParser(
        description="Generate a new COS module from the cc template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_module.py tech pem
  python generate_module.py zk auth --dry-run
        """,
    )

    parser.add_argument("domain", help="Domain name (e.g., tech, zk, publishing)")
    parser.add_argument("module", help="Module name (e.g., pem, auth)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()

    generate_module(args.domain.lower(), args.module.lower(), args.dry_run)


if __name__ == "__main__":
    main()
