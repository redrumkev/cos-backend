"""Tests for the module generator script."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to Python path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from generate_module import (
    _copy_template,
    _copy_test_template,
    _patch_alembic,
    _update_registry,
    _validate_name,
    generate_module,
    main,
)


class TestValidateName:
    """Test name validation function."""

    def test_valid_names(self) -> None:
        """Test that valid names pass validation."""
        # These should not raise
        _validate_name("tech", "Domain")
        _validate_name("pem", "Module")
        _validate_name("auth_manager", "Module")
        _validate_name("content_2", "Module")

    def test_empty_name(self) -> None:
        """Test that empty names are rejected."""
        with pytest.raises(ValueError, match="Domain name cannot be empty"):
            _validate_name("", "Domain")

    def test_invalid_format(self) -> None:
        """Test that invalid name formats are rejected."""
        # Capital letters
        with pytest.raises(ValueError, match="must start with lowercase letter"):
            _validate_name("Tech", "Domain")

        # Starting with number
        with pytest.raises(ValueError, match="must start with lowercase letter"):
            _validate_name("2tech", "Domain")

        # Invalid characters
        with pytest.raises(ValueError, match="must start with lowercase letter"):
            _validate_name("tech-pem", "Module")


class TestCopyTemplate:
    """Test template copying functionality."""

    def test_copy_python_files(self, tmp_path: Path) -> None:
        """Test copying and transforming Python files."""
        # Create source directory with test files
        source_dir = tmp_path / "cc"
        source_dir.mkdir()

        # Create test Python file
        cc_main = source_dir / "cc_main.py"
        cc_main.write_text(
            '"""Control Center module main."""\n'
            "from .router import router\n"
            'cc_app = FastAPI(title="Control Center API")\n'
            'tech_cc_label = "tech_cc"\n'
        )

        models_file = source_dir / "models.py"
        models_file.write_text('"""CC models."""\nclass CCModel:\n    pass\n')

        target_dir = tmp_path / "pem"

        # Test the copy function
        _copy_template(source_dir, target_dir, "pem", "tech")

        # Check main file was renamed
        pem_main = target_dir / "pem_main.py"
        assert pem_main.exists()
        content = pem_main.read_text()
        assert "Pem Module" in content
        assert "tech_pem" in content
        assert "cc" not in content.lower() or "Control Center" in content  # Transformed

        # Check other files
        assert (target_dir / "models.py").exists()
        models_content = (target_dir / "models.py").read_text()
        assert "PEMModel" in models_content

    def test_copy_yaml_files(self, tmp_path: Path) -> None:
        """Test copying and transforming YAML files."""
        source_dir = tmp_path / "cc"
        source_dir.mkdir()

        # Create test YAML file
        cc_map = source_dir / "cc_map.yaml"
        cc_map.write_text('module:\n  name: "cc"\n  label: "tech_cc"\n')

        target_dir = tmp_path / "pem"

        _copy_template(source_dir, target_dir, "pem", "tech")

        # Check YAML file was renamed and transformed
        pem_map = target_dir / "pem_map.yaml"
        assert pem_map.exists()
        content = pem_map.read_text()
        assert '"pem"' in content
        assert "tech_pem" in content

    def test_copy_template_failure(self, tmp_path: Path) -> None:
        """Test error handling in template copying."""
        source_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / "pem"

        # Should not raise error for empty source directory
        _copy_template(source_dir, target_dir, "pem", "tech")
        assert target_dir.exists()


class TestCopyTestTemplate:
    """Test test template copying functionality."""

    def test_copy_test_files(self, tmp_path: Path) -> None:
        """Test copying and transforming test files."""
        source_test_dir = tmp_path / "tests_cc"
        source_test_dir.mkdir()

        # Create test file
        test_file = source_test_dir / "test_models.py"
        test_file.write_text(
            "from src.backend.cc import models\n"
            "def test_cc_model():\n"
            "    models.cc_health_status()\n"
            '    assert "cc" in models.TABLE_NAME\n'
        )

        target_test_dir = tmp_path / "tests_pem"

        _copy_test_template(source_test_dir, target_test_dir, "pem")

        # Check __init__.py was created
        assert (target_test_dir / "__init__.py").exists()

        # Check test file was transformed
        copied_test = target_test_dir / "test_models.py"
        assert copied_test.exists()
        content = copied_test.read_text()
        assert "from src.backend.pem import models" in content
        assert "test_pem_model" in content
        assert 'assert "pem"' in content


class TestPatchAlembic:
    """Test alembic patching functionality."""

    def test_patch_alembic_success(self, tmp_path: Path) -> None:
        """Test successful alembic patching."""
        # Create alembic env.py
        migrations_dir = tmp_path / "src/db/migrations"
        migrations_dir.mkdir(parents=True)
        env_file = migrations_dir / "env.py"

        env_content = '''"""Alembic environment."""
from src.backend.cc import models as cc_models  # noqa: F401
from src.backend.cc import mem0_models as mem0_models

WATCH_SCHEMAS = {"cc", "mem0_cc"}
'''
        env_file.write_text(env_content)

        # Change working directory context
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            _patch_alembic("pem", "tech")

            # Check that imports were added
            updated_content = env_file.read_text()
            assert "from src.backend.pem import models as pem_models" in updated_content
            assert "from src.backend.pem import mem0_models as pem_mem0_models" in updated_content
            assert '"pem"' in updated_content
            assert '"mem0_pem"' in updated_content

        finally:
            os.chdir(original_cwd)

    def test_patch_alembic_missing_file(self, tmp_path: Path) -> None:
        """Test behavior when alembic env.py doesn't exist."""
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Should not raise error
            _patch_alembic("pem", "tech")

        finally:
            os.chdir(original_cwd)

    def test_patch_alembic_already_exists(self, tmp_path: Path) -> None:
        """Test behavior when module already exists in alembic."""
        migrations_dir = tmp_path / "src/db/migrations"
        migrations_dir.mkdir(parents=True)
        env_file = migrations_dir / "env.py"

        env_content = '''"""Alembic environment."""
from src.backend.cc import models as cc_models  # noqa: F401
from src.backend.pem import models as pem_models  # noqa: F401

WATCH_SCHEMAS = {"cc", "mem0_cc", "pem", "mem0_pem"}
'''
        env_file.write_text(env_content)

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Should handle gracefully
            _patch_alembic("pem", "tech")

        finally:
            os.chdir(original_cwd)


class TestUpdateRegistry:
    """Test registry update functionality."""

    def test_update_registry_success(self, tmp_path: Path) -> None:
        """Test successful registry update."""
        # Create registry file
        graph_dir = tmp_path / "src/graph"
        graph_dir.mkdir(parents=True)
        registry_file = graph_dir / "registry.py"

        registry_content = '''"""Neo4j registry."""
from enum import Enum

class ModuleLabel(str, Enum):
    """Module namespace labels."""

    TECH_CC = "tech_cc"
    # Future modules will be added here
'''
        registry_file.write_text(registry_content)

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            _update_registry("pem", "tech")

            # Check that new module was added
            updated_content = registry_file.read_text()
            assert 'PEM = "tech_pem"' in updated_content

        finally:
            os.chdir(original_cwd)

    def test_update_registry_missing_file(self, tmp_path: Path) -> None:
        """Test behavior when registry file doesn't exist."""
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Should not raise error
            _update_registry("pem", "tech")

        finally:
            os.chdir(original_cwd)


@pytest.mark.parametrize(
    "domain,module",
    [
        ("tech", "pem"),
        ("zk", "auth"),
        ("content", "manager"),
    ],
)
def test_generate_module_dry_run(domain: str, module: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test dry run functionality with different domain/module combinations."""
    # Create cc source directory
    cc_dir = tmp_path / "src/backend/cc"
    cc_dir.mkdir(parents=True)
    (cc_dir / "cc_main.py").write_text("# CC main")

    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)

        generate_module(domain, module, dry_run=True)

        captured = capsys.readouterr()
        assert f"DRY RUN: Would generate module {domain}_{module}" in captured.out

        # Should not create any files
        assert not (tmp_path / f"src/backend/{module}").exists()

    finally:
        os.chdir(original_cwd)


class TestGenerateModuleIntegration:
    """Integration tests for module generation."""

    def test_generate_module_success(self, tmp_path: Path) -> None:
        """Test full module generation process."""
        # Set up source structure
        self._setup_test_environment(tmp_path)

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            generate_module("tech", "pem", dry_run=False)

            # Verify module directory was created
            pem_dir = tmp_path / "src/backend/pem"
            assert pem_dir.exists()

            # Verify files were copied and transformed
            assert (pem_dir / "pem_main.py").exists()
            assert (pem_dir / "models.py").exists()

            # Verify test directory was created
            test_dir = tmp_path / "tests/backend/pem"
            assert test_dir.exists()
            assert (test_dir / "__init__.py").exists()

        finally:
            os.chdir(original_cwd)

    def test_generate_module_already_exists(self, tmp_path: Path) -> None:
        """Test error when module already exists."""
        self._setup_test_environment(tmp_path)

        # Create existing module
        pem_dir = tmp_path / "src/backend/pem"
        pem_dir.mkdir(parents=True)

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            with pytest.raises(SystemExit):
                generate_module("tech", "pem", dry_run=False)

        finally:
            os.chdir(original_cwd)

    def test_generate_module_no_cc_template(self, tmp_path: Path) -> None:
        """Test error when cc template doesn't exist."""
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            with pytest.raises(SystemExit):
                generate_module("tech", "pem", dry_run=False)

        finally:
            os.chdir(original_cwd)

    def test_generate_module_invalid_name(self) -> None:
        """Test error with invalid names."""
        with pytest.raises(SystemExit):
            generate_module("TECH", "pem", dry_run=False)

        with pytest.raises(SystemExit):
            generate_module("tech", "2pem", dry_run=False)

    def _setup_test_environment(self, tmp_path: Path) -> None:
        """Set up a complete test environment."""
        # Create cc source directory with files
        cc_dir = tmp_path / "src/backend/cc"
        cc_dir.mkdir(parents=True)

        (cc_dir / "cc_main.py").write_text(
            '"""Control Center module."""\ncc_app = FastAPI(title="Control Center API")\n'
        )
        (cc_dir / "models.py").write_text("# CC models")
        (cc_dir / "cc_map.yaml").write_text("name: cc")

        # Create cc test directory
        cc_test_dir = tmp_path / "tests/backend/cc"
        cc_test_dir.mkdir(parents=True)
        (cc_test_dir / "test_models.py").write_text("from src.backend.cc import models\ndef test_cc():\n    pass\n")

        # Create alembic env.py
        migrations_dir = tmp_path / "src/db/migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "env.py").write_text(
            'from src.backend.cc import models as cc_models  # noqa: F401\nWATCH_SCHEMAS = {"cc", "mem0_cc"}\n'
        )

        # Create registry file
        graph_dir = tmp_path / "src/graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "registry.py").write_text(
            'class ModuleLabel(str, Enum):\n    TECH_CC = "tech_cc"\n    # Future modules will be added here\n'
        )


class TestMainFunction:
    """Test the main CLI function."""

    @patch("sys.argv", ["generate_module.py", "tech", "pem"])
    def test_main_success(self, tmp_path: Path) -> None:
        """Test main function with valid arguments."""
        # Setup test environment
        cc_dir = tmp_path / "src/backend/cc"
        cc_dir.mkdir(parents=True)
        (cc_dir / "cc_main.py").write_text("# CC main")

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Should not raise
            main()

        except SystemExit:
            # Expected for successful completion
            pass
        finally:
            os.chdir(original_cwd)

    @patch("sys.argv", ["generate_module.py", "tech", "pem", "--dry-run"])
    def test_main_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main function with dry-run flag."""
        cc_dir = tmp_path / "src/backend/cc"
        cc_dir.mkdir(parents=True)
        (cc_dir / "cc_main.py").write_text("# CC main")

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            main()

            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out

        except SystemExit:
            pass  # Expected
        finally:
            os.chdir(original_cwd)

    @patch("sys.argv", ["generate_module.py"])
    def test_main_missing_args(self) -> None:
        """Test main function with missing arguments."""
        with pytest.raises(SystemExit):
            main()


@pytest.mark.slow
class TestSlowIntegration:
    """Slow integration tests."""

    def test_generate_multiple_modules(self, tmp_path: Path) -> None:
        """Test generating multiple modules in sequence."""
        # Set up complete environment
        self._setup_complete_environment(tmp_path)

        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Generate first module
            generate_module("tech", "pem", dry_run=False)
            assert (tmp_path / "src/backend/pem").exists()

            # Generate second module
            generate_module("zk", "auth", dry_run=False)
            assert (tmp_path / "src/backend/auth").exists()

            # Verify both modules exist
            assert (tmp_path / "src/backend/pem/pem_main.py").exists()
            assert (tmp_path / "src/backend/auth/auth_main.py").exists()

            # Check that alembic was updated for both
            env_content = (tmp_path / "src/db/migrations/env.py").read_text()
            assert "pem_models" in env_content
            assert "auth_models" in env_content

        finally:
            os.chdir(original_cwd)

    def _setup_complete_environment(self, tmp_path: Path) -> None:
        """Set up a complete test environment with all required files."""
        # Create comprehensive cc source
        cc_dir = tmp_path / "src/backend/cc"
        cc_dir.mkdir(parents=True)

        files_to_create = [
            ("cc_main.py", '"""Control Center."""\napp = FastAPI()'),
            ("models.py", "# Models"),
            ("schemas.py", "# Schemas"),
            ("router.py", "# Router"),
            ("services.py", "# Services"),
            ("crud.py", "# CRUD"),
            ("deps.py", "# Dependencies"),
            ("cc_map.yaml", "module: cc"),
        ]

        for filename, content in files_to_create:
            (cc_dir / filename).write_text(content)

        # Create test files
        cc_test_dir = tmp_path / "tests/backend/cc"
        cc_test_dir.mkdir(parents=True)

        test_files = [
            ("test_models.py", "from src.backend.cc import models"),
            ("test_router.py", "from src.backend.cc import router"),
        ]

        for filename, content in test_files:
            (cc_test_dir / filename).write_text(content)

        # Create infrastructure files
        migrations_dir = tmp_path / "src/db/migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "env.py").write_text(
            'from src.backend.cc import models as cc_models  # noqa: F401\nWATCH_SCHEMAS = {"cc", "mem0_cc"}\n'
        )

        graph_dir = tmp_path / "src/graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "registry.py").write_text(
            "from enum import Enum\n"
            "class ModuleLabel(str, Enum):\n"
            '    TECH_CC = "tech_cc"\n'
            "    # Future modules will be added here\n"
        )
