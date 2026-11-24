
import pytest
from sqlalchemy.orm import Session

from app.models.project import Project
from app.core.security import create_access_token
from app.models.task import Task


@pytest.fixture
def authenticated_user(client):
    """Register and log in a test user."""

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "projectuser@example.com",
            "password": "SecurePass123!",
        },
    )

    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "projectuser@example.com",
            "password": "SecurePass123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "user_id": user_id,
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }


def test_create_project_success(
    client,
    test_engine,
    authenticated_user,
):
    response = client.post(
        "/api/v1/projects",
        headers=authenticated_user["headers"],
        json={
            "name": "  TaskFlow Backend  ",
            "description": "FastAPI project management API",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "TaskFlow Backend"
    assert data["description"] == (
        "FastAPI project management API"
    )
    assert data["status"] == "active"
    assert data["owner_id"] == authenticated_user["user_id"]
    assert isinstance(data["id"], int)
    assert data["created_at"] is not None

    # Verify that the project was saved to the database
    with Session(test_engine) as db:
        saved_project = db.get(Project, data["id"])

        assert saved_project is not None
        assert saved_project.owner_id == (
            authenticated_user["user_id"]
        )


def test_create_project_without_token(client):
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Unauthorized Project",
            "description": "Test",
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "Unauthorized Ownership",
            "owner_id": 999,
        },
        {
            "name": "   ",
            "description": "Invalid project name",
        },
        {
            "name": "A" * 151,
            "description": "Name exceeds character limit",
        },
    ],
)
def test_create_project_invalid_data(
    client,
    authenticated_user,
    payload,
):
    response = client.post(
        "/api/v1/projects",
        headers=authenticated_user["headers"],
        json=payload,
    )

    assert response.status_code == 422


def create_test_project(client, headers, name):
    """Create a project through the API."""

    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": name,
            "description": "Test project",
        },
    )

    assert response.status_code == 201
    return response.json()


def create_second_user_headers(client):
    """Register another user and generate an access token."""

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "secondprojectuser@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201

    token = create_access_token(
        user_id=response.json()["id"],
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def test_list_only_own_projects(client, authenticated_user):
    own_headers = authenticated_user["headers"]

    create_test_project(client, own_headers, "Project A")
    create_test_project(client, own_headers, "Project B")

    other_headers = create_second_user_headers(client)
    create_test_project(client, other_headers, "Private Project")

    response = client.get(
        "/api/v1/projects",
        headers=own_headers,
    )

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 2
    assert [p["name"] for p in projects] == [
        "Project A",
        "Project B",
    ]

    assert all(
        p["owner_id"] == authenticated_user["user_id"]
        for p in projects
    )


def test_list_projects_empty(client, authenticated_user):
    response = client.get(
        "/api/v1/projects",
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_projects_pagination(client, authenticated_user):
    headers = authenticated_user["headers"]

    for name in ["Project A", "Project B", "Project C"]:
        create_test_project(client, headers, name)

    response = client.get(
        "/api/v1/projects",
        headers=headers,
        params={"offset": 1, "limit": 1},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Project B"


def test_get_own_project(client, authenticated_user):
    headers = authenticated_user["headers"]

    project = create_test_project(
        client, headers, "My Project"
    )

    response = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == project["id"]
    assert response.json()["name"] == "My Project"


def test_cannot_view_another_users_project(
    client,
    authenticated_user,
):
    project = create_test_project(
        client,
        authenticated_user["headers"],
        "Private Project",
    )

    other_headers = create_second_user_headers(client)

    response = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404


def test_get_nonexistent_project(
    client,
    authenticated_user,
):
    response = client.get(
        "/api/v1/projects/999999",
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/projects",
        "/api/v1/projects/1",
    ],
)
def test_project_get_requires_authentication(client, endpoint):
    response = client.get(endpoint)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {"offset": -1},
        {"limit": 101},
    ],
)
def test_invalid_project_pagination(
    client,
    authenticated_user,
    params,
):
    response = client.get(
        "/api/v1/projects",
        headers=authenticated_user["headers"],
        params=params,
    )

    assert response.status_code == 422


# -----------------------------------------
# Project update tests
# -----------------------------------------

def test_update_project_success(client, authenticated_user):
    headers = authenticated_user["headers"]

    project = create_test_project(
        client, headers, "Original Project"
    )

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={
            "name": "  Updated Project  ",
            "status": "completed",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project"
    assert response.json()["status"] == "completed"

    get_response = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Updated Project"
    assert get_response.json()["description"] == "Test project"


def test_clear_project_description(client, authenticated_user):
    headers = authenticated_user["headers"]

    project = create_test_project(
        client, headers, "My Project"
    )

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_empty_project_update(client, authenticated_user):
    headers = authenticated_user["headers"]

    project = create_test_project(
        client, headers, "Unchanged Project"
    )

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Unchanged Project"
    assert response.json()["status"] == "active"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": None},
        {"status": "invalid"},
        {"status": None},
        {"owner_id": 999},
    ],
)
def test_invalid_project_update(
    client,
    authenticated_user,
    payload,
):
    headers = authenticated_user["headers"]

    project = create_test_project(
        client, headers, "Valid Project"
    )

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422


def test_cannot_update_another_users_project(
    client,
    authenticated_user,
):
    project = create_test_project(
        client,
        authenticated_user["headers"],
        "Private Project",
    )

    other_headers = create_second_user_headers(client)

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=other_headers,
        json={"name": "Unauthorized Change"},
    )

    assert response.status_code == 404

    original = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=authenticated_user["headers"],
    )

    assert original.status_code == 200
    assert original.json()["name"] == "Private Project"


def test_update_nonexistent_project(client, authenticated_user):
    response = client.patch(
        "/api/v1/projects/999999",
        headers=authenticated_user["headers"],
        json={"name": "New Name"},
    )

    assert response.status_code == 404


def test_update_project_without_token(client):
    response = client.patch(
        "/api/v1/projects/1",
        json={"name": "Unauthorized"},
    )

    assert response.status_code == 401


# -----------------------------------------
# Project deletion tests
# -----------------------------------------

def test_delete_own_project(client, authenticated_user):
    headers = authenticated_user["headers"]

    project = create_test_project(
        client, headers, "Delete Me"
    )

    response = client.delete(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
    )

    assert get_response.status_code == 404


def test_cannot_delete_another_users_project(
    client,
    authenticated_user,
):
    project = create_test_project(
        client,
        authenticated_user["headers"],
        "Private Project",
    )

    other_headers = create_second_user_headers(client)

    response = client.delete(
        f"/api/v1/projects/{project['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404

    original = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=authenticated_user["headers"],
    )

    assert original.status_code == 200


def test_delete_nonexistent_project(client, authenticated_user):
    response = client.delete(
        "/api/v1/projects/999999",
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 404


def test_delete_project_without_token(client):
    response = client.delete("/api/v1/projects/1")

    assert response.status_code == 401


def test_deleting_project_cascades_to_tasks(
    client,
    test_engine,
    authenticated_user,
):
    headers = authenticated_user["headers"]

    # Create a project
    project = create_test_project(
        client,
        headers,
        "Cascade Test Project",
    )

    project_id = project["id"]

    # Create a task inside the project
    task_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Task To Be Deleted",
        },
    )

    assert task_response.status_code == 201

    task_id = task_response.json()["id"]

    # Verify SQLite foreign keys are enabled
    with test_engine.connect() as connection:
        foreign_keys_enabled = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

        assert foreign_keys_enabled == 1

    # Delete the parent project
    delete_response = client.delete(
        f"/api/v1/projects/{project_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    # Verify both records were deleted
    with Session(test_engine) as db:
        assert db.get(Project, project_id) is None
        assert db.get(Task, task_id) is None

