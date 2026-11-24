
import pytest

from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.task import Task


TEST_PASSWORD = "SecurePass123!"


def register_test_user(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 201

    user_id = response.json()["id"]

    token = create_access_token(user_id)

    return {
        "user_id": user_id,
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }


def create_test_project(client, headers):
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": "Test Project",
            "description": "Project for task testing",
        },
    )

    assert response.status_code == 201

    return response.json()


@pytest.fixture
def task_environment(client):
    user = register_test_user(
        client,
        "taskowner@example.com",
    )

    project = create_test_project(
        client,
        user["headers"],
    )

    return {
        "user": user,
        "project": project,
    }


def test_create_task_success(
    client,
    test_engine,
    task_environment,
):
    user = task_environment["user"]
    project = task_environment["project"]

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=user["headers"],
        json={
            "title": "  Write JWT Tests  ",
            "description": "Add security tests",
            "priority": "high",
            "due_date": "2026-12-15T18:00:00+03:00",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Write JWT Tests"
    assert data["description"] == "Add security tests"
    assert data["status"] == "todo"
    assert data["priority"] == "high"
    assert data["project_id"] == project["id"]
    assert data["due_date"] is not None
    assert data["created_at"] is not None

    with Session(test_engine) as db:
        saved_task = db.get(Task, data["id"])

        assert saved_task is not None
        assert saved_task.project_id == project["id"]


def test_create_task_defaults(client, task_environment):
    user = task_environment["user"]
    project = task_environment["project"]

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=user["headers"],
        json={
            "title": "Simple Task",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "todo"
    assert data["priority"] == "medium"
    assert data["description"] is None
    assert data["due_date"] is None


def test_create_task_requires_authentication(
    client,
    task_environment,
):
    project = task_environment["project"]

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Unauthorized Task"},
    )

    assert response.status_code == 401


def test_cannot_create_task_in_another_users_project(
    client,
    task_environment,
):
    project = task_environment["project"]

    other_user = register_test_user(
        client,
        "secondtaskuser@example.com",
    )

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=other_user["headers"],
        json={"title": "Unauthorized Task"},
    )

    assert response.status_code == 404


def test_create_task_unknown_project(
    client,
    task_environment,
):
    user = task_environment["user"]

    response = client.post(
        "/api/v1/projects/999999/tasks",
        headers=user["headers"],
        json={"title": "Orphan Task"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "A" * 151},
        {"title": "Invalid", "priority": "urgent"},
        {"title": "Invalid", "project_id": 999},
        {"title": "Invalid", "owner_id": 999},
        {"title": "Invalid", "due_date": "not-a-date"},
    ],
)
def test_create_task_invalid_data(
    client,
    task_environment,
    payload,
):
    user = task_environment["user"]
    project = task_environment["project"]

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=user["headers"],
        json=payload,
    )

    assert response.status_code == 422


# -----------------------------------------
# Task listing and retrieval tests
# -----------------------------------------

def create_test_task(client, project_id, headers, title):
    """Create a task through the API."""

    response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        json={"title": title},
    )

    assert response.status_code == 201
    return response.json()


def test_list_tasks_only_from_selected_project(
    client,
    task_environment,
):
    user = task_environment["user"]
    project = task_environment["project"]
    headers = user["headers"]

    create_test_task(
        client, project["id"], headers, "Task A"
    )
    create_test_task(
        client, project["id"], headers, "Task B"
    )

    second_project = create_test_project(client, headers)

    create_test_task(
        client,
        second_project["id"],
        headers,
        "Task In Other Project",
    )

    response = client.get(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=headers,
    )

    assert response.status_code == 200

    tasks = response.json()

    assert len(tasks) == 2
    assert [task["title"] for task in tasks] == [
        "Task A",
        "Task B",
    ]


def test_list_tasks_empty(client, task_environment):
    user = task_environment["user"]
    project = task_environment["project"]

    response = client.get(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=user["headers"],
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_pagination(client, task_environment):
    user = task_environment["user"]
    project_id = task_environment["project"]["id"]
    headers = user["headers"]

    for title in ["Task A", "Task B", "Task C"]:
        create_test_task(
            client, project_id, headers, title
        )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Task B"


def test_get_own_task(client, task_environment):
    user = task_environment["user"]
    project_id = task_environment["project"]["id"]
    headers = user["headers"]

    task = create_test_task(
        client,
        project_id,
        headers,
        "My Task",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]
    assert response.json()["title"] == "My Task"
    assert response.json()["project_id"] == project_id


def test_cannot_list_another_users_tasks(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    other_user = register_test_user(
        client,
        "otherlistuser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=other_user["headers"],
    )

    assert response.status_code == 404


def test_cannot_view_another_users_task(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]
    owner_headers = task_environment["user"]["headers"]

    task = create_test_task(
        client,
        project_id,
        owner_headers,
        "Private Task",
    )

    other_user = register_test_user(
        client,
        "otherviewuser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=other_user["headers"],
    )

    assert response.status_code == 404


def test_list_tasks_unknown_project(
    client,
    task_environment,
):
    response = client.get(
        "/api/v1/projects/999999/tasks",
        headers=task_environment["user"]["headers"],
    )

    assert response.status_code == 404


def test_get_nonexistent_task(client, task_environment):
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/999999",
        headers=task_environment["user"]["headers"],
    )

    assert response.status_code == 404


def test_cannot_view_task_through_wrong_project(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    first_project_id = task_environment["project"]["id"]

    task = create_test_task(
        client,
        first_project_id,
        headers,
        "Private Task",
    )

    second_project = create_test_project(
        client,
        headers,
    )

    response = client.get(
        f"/api/v1/projects/{second_project['id']}/tasks/{task['id']}",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/projects/1/tasks",
        "/api/v1/projects/1/tasks/1",
    ],
)
def test_read_tasks_requires_authentication(
    client,
    endpoint,
):
    response = client.get(endpoint)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {"offset": -1},
        {"limit": 101},
    ],
)
def test_invalid_task_pagination(
    client,
    task_environment,
    params,
):
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=task_environment["user"]["headers"],
        params=params,
    )

    assert response.status_code == 422


# -----------------------------------------
# Task update tests
# -----------------------------------------

def test_update_task_success(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, headers, "Original Task"
    )

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=headers,
        json={
            "title": "  Updated Task  ",
            "status": "in_progress",
            "priority": "high",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "Updated Task"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"

    saved = client.get(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=headers,
    )

    assert saved.status_code == 200
    assert saved.json()["title"] == "Updated Task"


def test_update_task_clear_optional_fields(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, headers, "Task With Date"
    )

    endpoint = (
        f"/api/v1/projects/{project_id}/tasks/{task['id']}"
    )

    first_response = client.patch(
        endpoint,
        headers=headers,
        json={
            "description": "Temporary description",
            "due_date": "2026-12-15T18:00:00+03:00",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["due_date"] is not None

    clear_response = client.patch(
        endpoint,
        headers=headers,
        json={
            "description": None,
            "due_date": None,
        },
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["description"] is None
    assert clear_response.json()["due_date"] is None


def test_empty_task_update(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, headers, "Unchanged Task"
    )

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=headers,
        json={},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Unchanged Task"
    assert response.json()["status"] == "todo"


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": None},
        {"title": "A" * 151},
        {"status": "blocked"},
        {"status": None},
        {"priority": "urgent"},
        {"project_id": 999},
        {"due_date": "2026-12-15T18:00:00"},
    ],
)
def test_invalid_task_update(
    client,
    task_environment,
    payload,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, headers, "Valid Task"
    )

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422


def test_cannot_update_another_users_task(
    client,
    task_environment,
):
    owner_headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, owner_headers, "Private Task"
    )

    other_user = register_test_user(
        client,
        "otherupdateuser@example.com",
    )

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=other_user["headers"],
        json={"title": "Unauthorized Update"},
    )

    assert response.status_code == 404

    original = client.get(
        f"/api/v1/projects/{project_id}/tasks/{task['id']}",
        headers=owner_headers,
    )

    assert original.status_code == 200
    assert original.json()["title"] == "Private Task"


def test_cannot_update_task_through_wrong_project(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    first_project = task_environment["project"]

    task = create_test_task(
        client,
        first_project["id"],
        headers,
        "Private Task",
    )

    second_project = create_test_project(client, headers)

    response = client.patch(
        f"/api/v1/projects/{second_project['id']}/tasks/{task['id']}",
        headers=headers,
        json={"title": "Wrong Project"},
    )

    assert response.status_code == 404


def test_update_nonexistent_task(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/999999",
        headers=headers,
        json={"title": "Missing Task"},
    )

    assert response.status_code == 404


def test_update_task_without_token(client):
    response = client.patch(
        "/api/v1/projects/1/tasks/1",
        json={"title": "Unauthorized"},
    )

    assert response.status_code == 401


# -----------------------------------------
# Task deletion tests
# -----------------------------------------

def test_delete_task_success(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, headers, "Delete Me"
    )

    endpoint = (
        f"/api/v1/projects/{project_id}/tasks/{task['id']}"
    )

    response = client.delete(
        endpoint,
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(
        endpoint,
        headers=headers,
    )

    assert get_response.status_code == 404


def test_cannot_delete_another_users_task(
    client,
    task_environment,
):
    owner_headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, owner_headers, "Private Task"
    )

    other_user = register_test_user(
        client,
        "otherdeleteuser@example.com",
    )

    endpoint = (
        f"/api/v1/projects/{project_id}/tasks/{task['id']}"
    )

    response = client.delete(
        endpoint,
        headers=other_user["headers"],
    )

    assert response.status_code == 404

    original = client.get(
        endpoint,
        headers=owner_headers,
    )

    assert original.status_code == 200


def test_cannot_delete_task_through_wrong_project(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client, project_id, headers, "Private Task"
    )

    second_project = create_test_project(client, headers)

    response = client.delete(
        f"/api/v1/projects/{second_project['id']}/tasks/{task['id']}",
        headers=headers,
    )

    assert response.status_code == 404


def test_delete_nonexistent_task(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    response = client.delete(
        f"/api/v1/projects/{project_id}/tasks/999999",
        headers=task_environment["user"]["headers"],
    )

    assert response.status_code == 404


def test_delete_task_without_token(client):
    response = client.delete(
        "/api/v1/projects/1/tasks/1"
    )

    assert response.status_code == 401
