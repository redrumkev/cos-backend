"""Tests for API router endpoints in the Control Center module.

This file contains tests for HTTP endpoints, ensuring that
router functions work correctly with various request scenarios.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


class TestModuleRouterEndpoints:
    """Test cases for Module router endpoints."""

    def test_create_module_success(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test creating a module via POST /modules."""
        module_name = f"test_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0", "config": '{"setting1": "value1"}'}

        response = test_client.post("/cc/modules", json=module_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == module_name
        assert data["version"] == "1.0.0"
        assert data["config"] == '{"setting1": "value1"}'
        assert data["active"] is True
        assert "id" in data
        assert "last_active" in data

    def test_create_module_minimal_data(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test creating a module with minimal required data."""
        module_name = f"minimal_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0"}

        response = test_client.post("/cc/modules", json=module_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == module_name
        assert data["version"] == "1.0.0"
        assert data["config"] is None

    def test_create_module_validation_error(self, test_client: TestClient) -> None:
        """Test creating a module with invalid data."""
        module_data = {
            "name": "",  # Empty name should fail validation
            "version": "1.0.0",
        }

        response = test_client.post("/cc/modules", json=module_data)

        assert response.status_code == 422  # Validation error

    def test_create_module_duplicate_name(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test creating a module with duplicate name."""
        module_name = f"duplicate_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0"}

        # Create first module
        response1 = test_client.post("/cc/modules", json=module_data)
        assert response1.status_code == 201

        # Try to create second module with same name
        response2 = test_client.post("/cc/modules", json=module_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    def test_list_modules_empty(self, test_client: TestClient) -> None:
        """Test listing modules when database is empty."""
        response = test_client.get("/cc/modules")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_modules_with_data(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test listing modules with data."""
        # Create multiple modules
        modules_data = [
            {"name": f"module_a_{unique_test_id}", "version": "1.0.0"},
            {"name": f"module_b_{unique_test_id}", "version": "2.0.0"},
            {"name": f"module_c_{unique_test_id}", "version": "1.5.0"},
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
        expected_names = [f"module_a_{unique_test_id}", f"module_b_{unique_test_id}", f"module_c_{unique_test_id}"]
        assert module_names == expected_names

    def test_list_modules_pagination(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test listing modules with pagination."""
        # Create multiple modules
        for i in range(5):
            module_data = {"name": f"module_{i:02d}_{unique_test_id}", "version": "1.0.0"}
            response = test_client.post("/cc/modules", json=module_data)
            assert response.status_code == 201

        # Test first page
        response = test_client.get("/cc/modules?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == f"module_00_{unique_test_id}"
        assert data[1]["name"] == f"module_01_{unique_test_id}"

        # Test second page
        response = test_client.get("/cc/modules?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == f"module_02_{unique_test_id}"
        assert data[1]["name"] == f"module_03_{unique_test_id}"

    def test_get_module_success(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test getting a specific module by ID."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Get the module by ID
        response = test_client.get(f"/cc/modules/{created_module['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_module["id"]
        assert data["name"] == module_name
        assert data["version"] == "1.0.0"

    def test_get_module_not_found(self, test_client: TestClient) -> None:
        """Test getting a module that doesn't exist."""
        fake_id = str(uuid4())
        response = test_client.get(f"/cc/modules/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_module_success(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test updating a module successfully."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0"}
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
        assert data["name"] == module_name  # Unchanged

    def test_update_module_partial(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test updating a module with partial data."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Update only the version
        update_data = {"version": "1.2.0"}
        response = test_client.patch(f"/cc/modules/{created_module['id']}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.2.0"
        assert data["name"] == module_name  # Unchanged
        assert data["active"] is True  # Unchanged

    def test_update_module_not_found(self, test_client: TestClient) -> None:
        """Test updating a module that doesn't exist."""
        fake_id = str(uuid4())
        update_data = {"version": "1.1.0"}
        response = test_client.patch(f"/cc/modules/{fake_id}", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_module_name_conflict(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test updating a module name to conflict with existing module."""
        # Create two modules
        module1_data = {"name": f"module_1_{unique_test_id}", "version": "1.0.0"}
        module2_data = {"name": f"module_2_{unique_test_id}", "version": "1.0.0"}

        create_response1 = test_client.post("/cc/modules", json=module1_data)
        assert create_response1.status_code == 201

        create_response2 = test_client.post("/cc/modules", json=module2_data)
        assert create_response2.status_code == 201
        module2 = create_response2.json()

        # Try to update module2's name to conflict with module1
        update_data = {"name": f"module_1_{unique_test_id}"}
        response = test_client.patch(f"/cc/modules/{module2['id']}", json=update_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_delete_module_success(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test deleting a module successfully."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        module_data = {"name": module_name, "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Delete the module
        response = test_client.delete(f"/cc/modules/{created_module['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_module["id"]

        # Verify it's deleted by trying to get it
        get_response = test_client.get(f"/cc/modules/{created_module['id']}")
        assert get_response.status_code == 404

    def test_delete_module_not_found(self, test_client: TestClient) -> None:
        """Test deleting a module that doesn't exist."""
        fake_id = str(uuid4())
        response = test_client.delete(f"/cc/modules/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_module_crud_workflow(self, test_client: TestClient, unique_test_id: str) -> None:
        """Test a complete CRUD workflow for modules."""
        module_name = f"workflow_module_{unique_test_id}"

        # Create
        create_data = {"name": module_name, "version": "1.0.0"}
        create_response = test_client.post("/cc/modules", json=create_data)
        assert create_response.status_code == 201
        module = create_response.json()

        # Read
        get_response = test_client.get(f"/cc/modules/{module['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == module_name

        # Update
        update_data = {"version": "1.1.0", "active": False}
        update_response = test_client.patch(f"/cc/modules/{module['id']}", json=update_data)
        assert update_response.status_code == 200
        updated_module = update_response.json()
        assert updated_module["version"] == "1.1.0"
        assert updated_module["active"] is False

        # Delete
        delete_response = test_client.delete(f"/cc/modules/{module['id']}")
        assert delete_response.status_code == 200

        # Verify deletion
        final_get_response = test_client.get(f"/cc/modules/{module['id']}")
        assert final_get_response.status_code == 404
