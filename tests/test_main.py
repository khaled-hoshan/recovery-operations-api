import pytest
from fastapi.testclient import TestClient
from app.main import app, operations


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_successful_creation():
    response = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["service_name"] == "payment-service"
    assert data["failure_type"] == "health_check_failed"


def test_invalid_creation():
    response = client.post(
        "/operations", json={"service_name": "", "failure_type": "health_check_failed"}
    )

    assert response.status_code == 422

@pytest.fixture(autouse=True)
def reset_operations():
    operations.clear()
    yield
    operations.clear()

def test_retrieve_operation():
    response = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"},
    )

    data = response.json()
    operation_id = data["id"]

    response2 = client.get(
        f"/operations/{operation_id}"
    )

    assert response2.status_code == 200
    assert response2.json()["id"] == operation_id
    assert response2.json()["service_name"] == "payment-service"

def test_retrieve_missing_operation():
    response = client.get(
        "/operations/nonexistent"
    )

    assert response.status_code == 404

def test_list_operations():
    response = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"}
    )

    response2 = client.post(
        "/operations",
        json={"service_name": "checkout-service", "failure_type": "health_check_failed"}
    )

    response3 = client.get(
        "/operations",
    )

    assert response3.status_code == 200
    assert len(response3.json()) == 2

def test_enforce_status_transitions():
    created = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"}
    )
    operation_id = created.json()["id"]

    first_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "running"}
    )

    assert first_update.status_code == 200
    assert first_update.json()["status"] == "running"

    second_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "running"}
    )

    assert second_update.status_code == 409

def test_successful_is_terminal():
    created = client.post(
        "/operations",
        json={"service_name": "payment-service", "failure_type": "health_check_failed"}
    )
    operation_id = created.json()["id"]

    first_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "running"}
    )
    second_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "succeeded"}
    )
    third_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "failed"}
    )

    assert first_update.status_code == 200
    assert second_update.status_code == 200
    assert third_update.status_code == 409

def test_failed_is_terminal():
    created = client.post(
        "/operations",
        json={"service_name": "checkout-service", "failure_type": "health_check_failed"}
    )
    operation_id = created.json()["id"]

    first_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "running"}
    )
    second_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "failed"}
    )
    third_update = client.patch(
        f"/operations/{operation_id}",
        json={"status": "succeeded"}
    )

    assert first_update.status_code == 200
    assert second_update.status_code == 200
    assert third_update.status_code == 409
