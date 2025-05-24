"""Tests for API router endpoints in the Control Center module.

This file contains tests for HTTP endpoints, ensuring that
router functions work correctly with various request scenarios.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestModuleRouterEndpoints:
    """Test cases for Module router endpoints."""

    def test_create_module_success(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test creating a module via POST /modules."""
        module_data = {"name": "test_module", "version": "1.0.0", "config": '{"setting1": "value1"}'}

        response = test_client.post("/cc/modules", json=module_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_module"
        assert data["version"] == "1.0.0"
        assert data["config"] == '{"setting1": "value1"}'
        assert data["active"] is True
        assert "id" in data
        assert "last_active" in data

    def test_create_module_minimal_data(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test creating a module with minimal required data."""
        module_data = {"name": "minimal_module", "version": "1.0.0"}

        response = test_client.post("/cc/modules", json=module_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "minimal_module"
        assert data["version"] == "1.0.0"
        assert data["config"] is None

    def test_create_module_validation_error(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test creating a module with invalid data."""
        module_data = {
            "name": "",  # Empty name should fail validation
            "version": "1.0.0",
        }

        response = test_client.post("/cc/modules", json=module_data)

        assert response.status_code == 422  # Validation error

    def test_create_module_duplicate_name(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test creating a module with duplicate name."""
        module_data = {"name": "duplicate_module", "version": "1.0.0"}

        # Create first module
        response1 = test_client.post("/cc/modules", json=module_data)
        assert response1.status_code == 201

        # Try to create second module with same name
        response2 = test_client.post("/cc/modules", json=module_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    def test_list_modules_empty(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test listing modules when database is empty."""
        response = test_client.get("/cc/modules")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_modules_with_data(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test listing modules with data."""
        # Create multiple modules
        modules_data = [
            {"name": "module_a", "version": "1.0.0"},
            {"name": "module_b", "version": "2.0.0"},
            {"name": "module_c", "version": "1.5.0"},
        ]

        for module_data in modules_data:
            response = test_client.post("/cc/modules", json=module_data)
            assert response.status_code == 201

        # List modules
        response = test_client.get("/cc/modules")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Should be ordered by name
        module_names = [module["name"] for module in data]
        assert module_names == ["module_a", "module_b", "module_c"]

    def test_list_modules_pagination(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test listing modules with pagination."""
        # Create multiple modules
        for i in range(5):
            module_data = {"name": f"module_{i:02d}", "version": "1.0.0"}
            response = test_client.post("/cc/modules", json=module_data)
            assert response.status_code == 201

        # Test first page
        response = test_client.get("/cc/modules?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "module_00"
        assert data[1]["name"] == "module_01"

        # Test second page
        response = test_client.get("/cc/modules?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "module_02"
        assert data[1]["name"] == "module_03"

    def test_get_module_success(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test getting a specific module by ID."""
        # Create a module first
        module_data = {"name": "test_module", "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Get the module by ID
        response = test_client.get(f"/cc/modules/{created_module['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_module["id"]
        assert data["name"] == "test_module"
        assert data["version"] == "1.0.0"

    def test_get_module_not_found(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test getting a module that doesn't exist."""
        fake_id = str(uuid4())
        response = test_client.get(f"/cc/modules/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_module_success(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test updating a module successfully."""
        # Create a module first
        module_data = {"name": "test_module", "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Update the module
        update_data = {"version": "1.1.0", "active": False}
        response = test_client.patch(f"/cc/modules/{created_module['id']}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_module["id"]
        assert data["version"] == "1.1.0"
        assert data["active"] is False
        assert data["name"] == "test_module"  # Unchanged

    def test_update_module_partial(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test updating a module with partial data."""
        # Create a module first
        module_data = {"name": "test_module", "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Update only the version
        update_data = {"version": "1.2.0"}
        response = test_client.patch(f"/cc/modules/{created_module['id']}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.2.0"
        assert data["name"] == "test_module"  # Unchanged
        assert data["active"] is True  # Unchanged

    def test_update_module_not_found(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test updating a module that doesn't exist."""
        fake_id = str(uuid4())
        update_data = {"version": "1.1.0"}
        response = test_client.patch(f"/cc/modules/{fake_id}", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_module_name_conflict(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test updating a module name to one that already exists."""
        # Create two modules
        module1_data = {"name": "module_1", "version": "1.0.0"}
        create_response1 = test_client.post("/cc/modules", json=module1_data)
        assert create_response1.status_code == 201
        module1 = create_response1.json()

        module2_data = {"name": "module_2", "version": "1.0.0"}
        create_response2 = test_client.post("/cc/modules", json=module2_data)
        assert create_response2.status_code == 201

        # Try to update module1's name to module_2
        update_data = {"name": "module_2"}
        response = test_client.patch(f"/cc/modules/{module1['id']}", json=update_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_delete_module_success(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test deleting a module successfully."""
        # Create a module first
        module_data = {"name": "test_module", "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Delete the module
        response = test_client.delete(f"/cc/modules/{created_module['id']}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

        # Verify it's actually deleted
        get_response = test_client.get(f"/cc/modules/{created_module['id']}")
        assert get_response.status_code == 404

    def test_delete_module_not_found(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test deleting a module that doesn't exist."""
        fake_id = str(uuid4())
        response = test_client.delete(f"/cc/modules/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_module_crud_workflow(self, test_client: TestClient, override_get_cc_db: AsyncSession) -> None:
        """Test complete CRUD workflow for modules."""
        # Create
        module_data = {"name": "workflow_module", "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()
        module_id = created_module["id"]

        # Read
        get_response = test_client.get(f"/cc/modules/{module_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "workflow_module"

        # Update
        update_data = {"version": "2.0.0", "config": '{"updated": true}'}
        update_response = test_client.patch(f"/cc/modules/{module_id}", json=update_data)
        assert update_response.status_code == 200
        updated_module = update_response.json()
        assert updated_module["version"] == "2.0.0"
        assert updated_module["config"] == '{"updated": true}'

        # List (should include our module)
        list_response = test_client.get("/cc/modules")
        assert list_response.status_code == 200
        modules = list_response.json()
        module_names = [m["name"] for m in modules]
        assert "workflow_module" in module_names

        # Delete
        delete_response = test_client.delete(f"/cc/modules/{module_id}")
        assert delete_response.status_code == 200

        # Verify deletion
        final_get_response = test_client.get(f"/cc/modules/{module_id}")
        assert final_get_response.status_code == 404
