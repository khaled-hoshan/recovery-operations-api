from datetime import datetime
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_successful_creation(client):
    response = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["service_name"] == "payment-service"
    assert data["failure_type"] == "health_check_failed"
    assert data["status"] == "pending"
    assert data["created_at"] is not None
    assert datetime.fromisoformat(data["created_at"])


def test_invalid_creation(client):
    response = client.post(
        "/operations", json={"service_name": "", "failure_type": "health_check_failed"}
    )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Request validation failed"
    assert len(body["details"]) > 0


def test_retrieve_operation(client):
    response = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )

    data = response.json()
    operation_id = data["id"]

    response2 = client.get(f"/operations/{operation_id}")
    update = client.patch(f"/operations/{operation_id}", json={"status": "running"})
    response3 = client.get(f"/operations/{operation_id}")

    assert response2.status_code == 200
    assert response2.json()["status"] == "pending"
    assert update.status_code == 200
    assert response3.status_code == 200
    assert response3.json()["id"] == operation_id
    assert response3.json()["service_name"] == "payment-service"
    assert response3.json()["status"] == "running"


def test_retrieve_missing_operation(client):
    response = client.get("/operations/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "OPERATION_NOT_FOUND"


def test_list_operations(client):
    client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )

    client.post(
        "/operations",
        json={
            "service_name": "checkout-service",
            "failure_type": "health_check_failed",
        },
    )

    response3 = client.get(
        "/operations",
    )

    assert response3.status_code == 200
    assert len(response3.json()) == 2


def test_enforce_status_transitions(client):
    created = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )
    operation_id = created.json()["id"]

    first_update = client.patch(
        f"/operations/{operation_id}", json={"status": "running"}
    )

    assert first_update.status_code == 200
    assert first_update.json()["status"] == "running"

    second_update = client.patch(
        f"/operations/{operation_id}", json={"status": "running"}
    )

    assert second_update.status_code == 409
    assert second_update.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_successful_is_terminal(client):
    created = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )
    operation_id = created.json()["id"]

    first_update = client.patch(
        f"/operations/{operation_id}", json={"status": "running"}
    )
    second_update = client.patch(
        f"/operations/{operation_id}", json={"status": "succeeded"}
    )
    third_update = client.patch(
        f"/operations/{operation_id}", json={"status": "failed"}
    )

    assert first_update.status_code == 200
    assert second_update.status_code == 200
    assert third_update.status_code == 409
    assert third_update.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_failed_is_terminal(client):
    created = client.post(
        "/operations",
        json={
            "service_name": "checkout-service",
            "failure_type": "health_check_failed",
        },
    )
    operation_id = created.json()["id"]

    first_update = client.patch(
        f"/operations/{operation_id}", json={"status": "running"}
    )
    second_update = client.patch(
        f"/operations/{operation_id}", json={"status": "failed"}
    )
    third_update = client.patch(
        f"/operations/{operation_id}", json={"status": "succeeded"}
    )

    assert first_update.status_code == 200
    assert second_update.status_code == 200
    assert third_update.status_code == 409
    assert third_update.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_missing_required_field(client):
    response = client.post(
        "/operations",
        json={"service_name": "payment-service"},
    )

    assert response.status_code == 422

    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Request validation failed"
    assert any(error["field"] == "body.failure_type" for error in body["details"])


def test_service_name_too_long(client):
    response = client.post(
        "/operations",
        json={
            "service_name": "a" * 101,
            "failure_type": "health_check_failed",
        },
    )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Request validation failed"
    assert len(body["details"]) > 0


def test_invalid_status_value(client):
    created = client.post(
        "/operations",
        json={
            "service_name": "payment-service",
            "failure_type": "health_check_failed",
        },
    )

    operation_id = created.json()["id"]

    response = client.patch(
        f"/operations/{operation_id}",
        json={"status": "unknown"},
    )

    assert response.status_code == 422

    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert any(error["field"] == "body.status" for error in body["details"])


def test_update_missing_operation(client):
    response = client.patch(
        "/operations/00000000-0000-0000-0000-000000000001",
        json={"status": "running"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "OPERATION_NOT_FOUND"
    assert response.json()["error"]["message"] == "Operation not found"


def test_database_error_during_creation(client):
    with patch("app.main.Session.commit", side_effect=SQLAlchemyError):
        response = client.post(
            "/operations",
            json={
                "service_name": "payment-service",
                "failure_type": "health_check_failed",
            },
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert (
        response.json()["error"]["message"] == "Database error while creating operation"
    )
