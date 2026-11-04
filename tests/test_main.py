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


def test_invalid_creation(client):
    response = client.post(
        "/operations", json={"service_name": "", "failure_type": "health_check_failed"}
    )

    assert response.status_code == 422


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
