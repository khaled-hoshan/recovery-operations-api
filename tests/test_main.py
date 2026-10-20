from fastapi.testclient import TestClient
from app.main import app

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
