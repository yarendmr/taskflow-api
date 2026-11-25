
import pytest

from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.task import Task
from datetime import datetime, timedelta, timezone


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


# -----------------------------------------
# Day 9 - Task filtering tests
# -----------------------------------------


def test_filter_tasks_by_status(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "Pending Task"
    )
    second = create_test_task(
        client, project_id, headers, "Completed Task"
    )

    update = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{second['id']}",
        headers=headers,
        json={"status": "done"},
    )
    assert update.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"status": "done"},
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        second["id"]
    ]


def test_filter_tasks_by_priority(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    low_task = create_test_task(
        client, project_id, headers, "Low Priority"
    )
    high_task = create_test_task(
        client, project_id, headers, "High Priority"
    )

    update = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{high_task['id']}",
        headers=headers,
        json={"priority": "high"},
    )
    assert update.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"priority": "high"},
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        high_task["id"]
    ]


def test_filter_tasks_by_status_and_priority(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "Todo High"
    )
    second = create_test_task(
        client, project_id, headers, "Done High"
    )
    third = create_test_task(
        client, project_id, headers, "Todo Medium"
    )

    for task in (first, second):
        response = client.patch(
            f"/api/v1/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"priority": "high"},
        )
        assert response.status_code == 200

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{second['id']}",
        headers=headers,
        json={"status": "done"},
    )
    assert response.status_code == 200

    result = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "status": "todo",
            "priority": "high",
        },
    )

    assert result.status_code == 200
    assert [task["id"] for task in result.json()] == [
        first["id"]
    ]


def test_task_filter_no_matches(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_test_task(
        client, project_id, headers, "Pending Task"
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"status": "done"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_task_filters_apply_before_pagination(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "First Pending"
    )
    completed = create_test_task(
        client, project_id, headers, "Completed"
    )
    third = create_test_task(
        client, project_id, headers, "Second Pending"
    )

    update = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{completed['id']}",
        headers=headers,
        json={"status": "done"},
    )
    assert update.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "status": "todo",
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        third["id"]
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"status": "blocked"},
        {"priority": "urgent"},
    ],
)
def test_invalid_task_filter_values(
    client,
    task_environment,
    params,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params=params,
    )

    assert response.status_code == 422


def test_task_filters_cannot_bypass_ownership(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    other_user = register_test_user(
        client,
        "day9filteruser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=other_user["headers"],
        params={
            "status": "todo",
            "priority": "high",
        },
    )

    assert response.status_code == 404


# -----------------------------------------
# Day 9 - Task search tests
# -----------------------------------------


def test_search_tasks_by_title(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    matching = create_test_task(
        client, project_id, headers, "Write JWT Tests"
    )
    create_test_task(
        client, project_id, headers, "Docker Setup"
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"search": "jwt"},
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        matching["id"]
    ]


def test_search_combined_with_filters(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    matching = create_test_task(
        client, project_id, headers, "JWT Security Tests"
    )
    other = create_test_task(
        client, project_id, headers, "JWT Documentation"
    )

    for task in (matching, other):
        response = client.patch(
            f"/api/v1/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"priority": "high"},
        )
        assert response.status_code == 200

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{other['id']}",
        headers=headers,
        json={"status": "done"},
    )
    assert response.status_code == 200

    result = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "search": "jwt",
            "status": "todo",
            "priority": "high",
        },
    )

    assert result.status_code == 200
    assert [task["id"] for task in result.json()] == [
        matching["id"]
    ]


def test_search_before_pagination(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_test_task(
        client, project_id, headers, "JWT First"
    )
    create_test_task(
        client, project_id, headers, "Other Task"
    )
    expected = create_test_task(
        client, project_id, headers, "JWT Second"
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "search": "JWT",
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        expected["id"]
    ]


def test_search_no_matches(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_test_task(
        client, project_id, headers, "Docker Setup"
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"search": "kubernetes"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_trims_whitespace(client, task_environment):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    expected = create_test_task(
        client, project_id, headers, "JWT Tests"
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"search": "  JWT  "},
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        expected["id"]
    ]


@pytest.mark.parametrize(
    "search",
    [
        "",
        "   ",
        "x" * 101,
    ],
)
def test_invalid_task_search(
    client,
    task_environment,
    search,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"search": search},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "search,matching_title,other_title",
    [
        ("%", "100% Complete", "100 Complete"),
        ("_", "needs_review", "needs review"),
    ],
)
def test_search_special_characters_are_literal(
    client,
    task_environment,
    search,
    matching_title,
    other_title,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    matching = create_test_task(
        client, project_id, headers, matching_title
    )
    create_test_task(
        client, project_id, headers, other_title
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"search": search},
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        matching["id"]
    ]


def test_search_cannot_bypass_project_ownership(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    other_user = register_test_user(
        client,
        "day9searchuser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=other_user["headers"],
        params={"search": "JWT"},
    )

    assert response.status_code == 404


def test_search_requires_authentication(client):
    response = client.get(
        "/api/v1/projects/1/tasks",
        params={"search": "JWT"},
    )

    assert response.status_code == 401


# -----------------------------------------
# Day 9 - Task sorting tests
# -----------------------------------------


def test_default_task_order_is_unchanged(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "Zulu Task"
    )
    second = create_test_task(
        client, project_id, headers, "Alpha Task"
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        first["id"],
        second["id"],
    ]


@pytest.mark.parametrize(
    "sort_order, expected_titles",
    [
        ("asc", ["Alpha", "beta", "Zulu"]),
        ("desc", ["Zulu", "beta", "Alpha"]),
    ],
)
def test_sort_tasks_by_title(
    client,
    task_environment,
    sort_order,
    expected_titles,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    for title in ["Zulu", "beta", "Alpha"]:
        create_test_task(client, project_id, headers, title)

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "title",
            "sort_order": sort_order,
        },
    )

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == (
        expected_titles
    )


@pytest.mark.parametrize(
    "sort_order, expected_priorities",
    [
        ("asc", ["low", "medium", "high"]),
        ("desc", ["high", "medium", "low"]),
    ],
)
def test_sort_tasks_by_priority(
    client,
    task_environment,
    sort_order,
    expected_priorities,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    for priority in ["medium", "high", "low"]:
        task = create_test_task(
            client,
            project_id,
            headers,
            f"{priority} Task",
        )

        update = client.patch(
            f"/api/v1/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"priority": priority},
        )
        assert update.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "priority",
            "sort_order": sort_order,
        },
    )

    assert response.status_code == 200
    assert [t["priority"] for t in response.json()] == (
        expected_priorities
    )


@pytest.mark.parametrize(
    "sort_order, reverse",
    [
        ("asc", False),
        ("desc", True),
    ],
)
def test_sort_tasks_by_created_at(
    client,
    test_engine,
    task_environment,
    sort_order,
    reverse,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "February Task"
    )
    second = create_test_task(
        client, project_id, headers, "January Task"
    )

    # Set deterministic timestamps in the isolated test DB.
    with Session(test_engine) as db:
        february_task = db.get(Task, first["id"])
        january_task = db.get(Task, second["id"])

        assert february_task is not None
        assert january_task is not None

        february_task.created_at = datetime(
            2026, 2, 1, tzinfo=timezone.utc
        )
        january_task.created_at = datetime(
            2026, 1, 1, tzinfo=timezone.utc
        )
        db.commit()

    expected = [second["id"], first["id"]]

    if reverse:
        expected.reverse()

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "created_at",
            "sort_order": sort_order,
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == expected


def test_sort_tasks_uses_stable_tie_breaker(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    tasks = [
        create_test_task(
            client, project_id, headers, f"Task {i}"
        )
        for i in range(3)
    ]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "priority",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        t["id"] for t in tasks
    ]


def test_sorting_applies_before_pagination(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_test_task(client, project_id, headers, "Z Task")
    expected = create_test_task(
        client, project_id, headers, "B Task"
    )
    create_test_task(client, project_id, headers, "A Task")

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "title",
            "sort_order": "asc",
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        expected["id"]
    ]


def test_sorting_combined_with_search_and_filters(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    zulu = create_test_task(
        client, project_id, headers, "JWT Zulu"
    )
    alpha = create_test_task(
        client, project_id, headers, "JWT Alpha"
    )

    create_test_task(
        client, project_id, headers, "JWT Medium"
    )
    create_test_task(
        client, project_id, headers, "Docker Alpha"
    )

    for task in (zulu, alpha):
        update = client.patch(
            f"/api/v1/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"priority": "high"},
        )
        assert update.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "search": "jwt",
            "status": "todo",
            "priority": "high",
            "sort_by": "title",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        alpha["id"],
        zulu["id"],
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "unknown"},
        {"sort_order": "sideways"},
    ],
)
def test_invalid_task_sort_parameters(
    client,
    task_environment,
    params,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params=params,
    )

    assert response.status_code == 422


def test_sorting_cannot_bypass_project_ownership(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    other_user = register_test_user(
        client,
        "day9sortuser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=other_user["headers"],
        params={
            "sort_by": "priority",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 404


def test_sorting_requires_authentication(client):
    response = client.get(
        "/api/v1/projects/1/tasks",
        params={
            "sort_by": "title",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 401


# -----------------------------------------
# Day 10 - Task Statistics Tests
# -----------------------------------------


def update_task_for_stats(
    client,
    project_id,
    headers,
    task_id,
    **fields,
):
    """Update a task during statistics tests."""

    response = client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task_id}",
        headers=headers,
        json=fields,
    )

    assert response.status_code == 200
    return response.json()


def test_task_stats_empty_project(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/stats",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "project_id": project_id,
        "total_tasks": 0,
        "todo_tasks": 0,
        "in_progress_tasks": 0,
        "done_tasks": 0,
        "low_priority_tasks": 0,
        "medium_priority_tasks": 0,
        "high_priority_tasks": 0,
        "completion_rate": 0.0,
    }


def test_task_stats_correct_counts(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    tasks = [
        create_test_task(
            client,
            project_id,
            headers,
            f"Task {i}",
        )
        for i in range(5)
    ]

    # Two completed, high-priority tasks.
    for task in tasks[:2]:
        update_task_for_stats(
            client,
            project_id,
            headers,
            task["id"],
            status="done",
            priority="high",
        )

    # One in-progress, low-priority task.
    update_task_for_stats(
        client,
        project_id,
        headers,
        tasks[2]["id"],
        status="in_progress",
        priority="low",
    )

    # One pending, low-priority task.
    update_task_for_stats(
        client,
        project_id,
        headers,
        tasks[3]["id"],
        priority="low",
    )

    # Fifth task remains todo / medium.

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/stats",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["project_id"] == project_id
    assert data["total_tasks"] == 5

    assert data["todo_tasks"] == 2
    assert data["in_progress_tasks"] == 1
    assert data["done_tasks"] == 2

    assert data["low_priority_tasks"] == 2
    assert data["medium_priority_tasks"] == 1
    assert data["high_priority_tasks"] == 2

    assert data["completion_rate"] == 40.0


def test_task_stats_completion_rate_rounding(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    tasks = [
        create_test_task(
            client,
            project_id,
            headers,
            f"Task {i}",
        )
        for i in range(3)
    ]

    update_task_for_stats(
        client,
        project_id,
        headers,
        tasks[0]["id"],
        status="done",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/stats",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total_tasks"] == 3
    assert response.json()["done_tasks"] == 1
    assert response.json()["completion_rate"] == 33.33


def test_task_stats_reflect_task_updates(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    task = create_test_task(
        client,
        project_id,
        headers,
        "Update Statistics",
    )

    endpoint = (
        f"/api/v1/projects/{project_id}/tasks/stats"
    )

    before = client.get(
        endpoint,
        headers=headers,
    )

    assert before.status_code == 200
    assert before.json()["todo_tasks"] == 1
    assert before.json()["completion_rate"] == 0.0

    update_task_for_stats(
        client,
        project_id,
        headers,
        task["id"],
        status="done",
        priority="high",
    )

    after = client.get(
        endpoint,
        headers=headers,
    )

    assert after.status_code == 200

    data = after.json()

    assert data["total_tasks"] == 1
    assert data["todo_tasks"] == 0
    assert data["done_tasks"] == 1
    assert data["medium_priority_tasks"] == 0
    assert data["high_priority_tasks"] == 1
    assert data["completion_rate"] == 100.0


def test_task_stats_reflect_task_deletion(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "First Task"
    )
    create_test_task(
        client, project_id, headers, "Second Task"
    )

    delete_response = client.delete(
        f"/api/v1/projects/{project_id}/tasks/{first['id']}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/stats",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_tasks"] == 1
    assert data["todo_tasks"] == 1
    assert data["medium_priority_tasks"] == 1


def test_task_stats_isolated_between_projects(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    first_project_id = task_environment["project"]["id"]

    second_project = create_test_project(
        client,
        headers,
    )
    second_project_id = second_project["id"]

    create_test_task(
        client,
        first_project_id,
        headers,
        "First Project Task",
    )

    create_test_task(
        client,
        second_project_id,
        headers,
        "Second Project Task A",
    )
    create_test_task(
        client,
        second_project_id,
        headers,
        "Second Project Task B",
    )

    first_response = client.get(
        f"/api/v1/projects/{first_project_id}/tasks/stats",
        headers=headers,
    )

    second_response = client.get(
        f"/api/v1/projects/{second_project_id}/tasks/stats",
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json()["total_tasks"] == 1
    assert second_response.json()["total_tasks"] == 2


def test_task_stats_cannot_access_another_users_project(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    other_user = register_test_user(
        client,
        "day10statsuser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks/stats",
        headers=other_user["headers"],
    )

    assert response.status_code == 404


def test_task_stats_nonexistent_project(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]

    response = client.get(
        "/api/v1/projects/999999/tasks/stats",
        headers=headers,
    )

    assert response.status_code == 404


def test_task_stats_requires_authentication(client):
    response = client.get(
        "/api/v1/projects/1/tasks/stats"
    )

    assert response.status_code == 401


# -----------------------------------------
# Day 11 - Deadline Filtering and Sorting
# -----------------------------------------


def create_deadline_task(
    client,
    project_id,
    headers,
    title,
    days_from_now=None,
    task_status=None,
    priority=None,
):
    """Create a task and optionally configure its deadline."""

    task = create_test_task(
        client,
        project_id,
        headers,
        title,
    )

    update_data = {}

    if days_from_now is not None:
        due_date = datetime.now(timezone.utc) + timedelta(
            days=days_from_now
        )
        update_data["due_date"] = due_date.isoformat()

    if task_status is not None:
        update_data["status"] = task_status

    if priority is not None:
        update_data["priority"] = priority

    if update_data:
        response = client.patch(
            f"/api/v1/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json=update_data,
        )

        assert response.status_code == 200
        return response.json()

    return task


def test_deadline_overdue_excludes_completed_tasks(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    overdue = create_deadline_task(
        client, project_id, headers, "Overdue Task",
        days_from_now=-2,
    )

    create_deadline_task(
        client, project_id, headers, "Completed Task",
        days_from_now=-3,
        task_status="done",
    )

    create_deadline_task(
        client, project_id, headers, "Future Task",
        days_from_now=3,
    )

    create_deadline_task(
        client, project_id, headers, "No Date Task",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"deadline": "overdue"},
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        overdue["id"]
    ]


def test_deadline_due_soon_seven_day_window(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_deadline_task(
        client, project_id, headers, "Tomorrow",
        days_from_now=1,
    )

    second = create_deadline_task(
        client, project_id, headers, "In Six Days",
        days_from_now=6,
        task_status="in_progress",
    )

    create_deadline_task(
        client, project_id, headers, "Too Late",
        days_from_now=9,
    )

    create_deadline_task(
        client, project_id, headers, "Already Overdue",
        days_from_now=-1,
    )

    create_deadline_task(
        client, project_id, headers, "Completed",
        days_from_now=2,
        task_status="done",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"deadline": "due_soon"},
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        first["id"],
        second["id"],
    ]


def test_deadline_no_due_date_includes_completed(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_deadline_task(
        client, project_id, headers, "Undated Task",
    )

    second = create_deadline_task(
        client, project_id, headers, "Completed Undated",
        task_status="done",
    )

    create_deadline_task(
        client, project_id, headers, "Dated Task",
        days_from_now=2,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"deadline": "no_due_date"},
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        first["id"],
        second["id"],
    ]


@pytest.mark.parametrize(
    "deadline",
    ["late", "tomorrow", ""],
)
def test_invalid_deadline_filter(
    client,
    task_environment,
    deadline,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"deadline": deadline},
    )

    assert response.status_code == 422


def test_deadline_filter_requires_authentication(client):
    response = client.get(
        "/api/v1/projects/1/tasks",
        params={"deadline": "overdue"},
    )

    assert response.status_code == 401


def test_deadline_filter_unknown_project(
    client,
    task_environment,
):
    response = client.get(
        "/api/v1/projects/999999/tasks",
        headers=task_environment["user"]["headers"],
        params={"deadline": "overdue"},
    )

    assert response.status_code == 404


def test_deadline_filter_cannot_bypass_ownership(
    client,
    task_environment,
):
    project_id = task_environment["project"]["id"]

    other_user = register_test_user(
        client,
        "day11deadlineuser@example.com",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=other_user["headers"],
        params={"deadline": "overdue"},
    )

    assert response.status_code == 404


def test_deadline_filter_isolated_by_project(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    first_project_id = task_environment["project"]["id"]

    second_project = create_test_project(client, headers)

    first = create_deadline_task(
        client, first_project_id, headers, "First Project",
        days_from_now=-2,
    )

    create_deadline_task(
        client, second_project["id"], headers,
        "Second Project",
        days_from_now=-2,
    )

    response = client.get(
        f"/api/v1/projects/{first_project_id}/tasks",
        headers=headers,
        params={"deadline": "overdue"},
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        first["id"]
    ]


def test_deadline_combined_with_existing_filters(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    matching = create_deadline_task(
        client, project_id, headers, "JWT Security",
        days_from_now=-2,
        priority="high",
    )

    create_deadline_task(
        client, project_id, headers, "JWT Completed",
        days_from_now=-2,
        task_status="done",
        priority="high",
    )

    create_deadline_task(
        client, project_id, headers, "Docker Security",
        days_from_now=-2,
        priority="high",
    )

    create_deadline_task(
        client, project_id, headers, "JWT Medium",
        days_from_now=-2,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "deadline": "overdue",
            "status": "todo",
            "priority": "high",
            "search": "jwt",
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        matching["id"]
    ]


def test_deadline_filter_before_pagination(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_deadline_task(
        client, project_id, headers, "First Overdue",
        days_from_now=-3,
    )

    create_deadline_task(
        client, project_id, headers, "Future Task",
        days_from_now=5,
    )

    expected = create_deadline_task(
        client, project_id, headers, "Second Overdue",
        days_from_now=-1,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "deadline": "overdue",
            "offset": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        expected["id"]
    ]


@pytest.mark.parametrize(
    "sort_order, expected_titles",
    [
        ("asc", ["Soon", "Middle", "Far", "No Date"]),
        ("desc", ["Far", "Middle", "Soon", "No Date"]),
    ],
)
def test_sort_tasks_by_due_date(
    client,
    task_environment,
    sort_order,
    expected_titles,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_deadline_task(
        client, project_id, headers, "Far",
        days_from_now=10,
    )

    create_deadline_task(
        client, project_id, headers, "No Date",
    )

    create_deadline_task(
        client, project_id, headers, "Soon",
        days_from_now=1,
    )

    create_deadline_task(
        client, project_id, headers, "Middle",
        days_from_now=5,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "due_date",
            "sort_order": sort_order,
        },
    )

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == (
        expected_titles
    )


def test_due_date_sorting_uses_stable_tie_breaker(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    first = create_test_task(
        client, project_id, headers, "First Task"
    )
    second = create_test_task(
        client, project_id, headers, "Second Task"
    )

    same_date = "2030-01-01T12:00:00+00:00"

    for task in (first, second):
        update = client.patch(
            f"/api/v1/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"due_date": same_date},
        )
        assert update.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={
            "sort_by": "due_date",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [
        first["id"],
        second["id"],
    ]


def test_deadline_filter_no_matches(
    client,
    task_environment,
):
    headers = task_environment["user"]["headers"]
    project_id = task_environment["project"]["id"]

    create_deadline_task(
        client, project_id, headers, "Future Task",
        days_from_now=10,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        params={"deadline": "overdue"},
    )

    assert response.status_code == 200
    assert response.json() == []
