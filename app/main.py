from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel, Field
import uuid
from typing import Literal

ALLOWED_TRANSITIONS = {
    "pending": ["running"],
    "running": ["succeeded", "failed"],
    "succeeded": [],
    "failed": [],
}

app = FastAPI(title="Recovery Operations API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


class OperationCreate(BaseModel):
    service_name: str = Field(min_length=1, max_length=100)
    failure_type: str = Field(min_length=1, max_length=100)


class OperationResponse(BaseModel):
    id: str
    service_name: str
    failure_type: str
    status: str


class OperationStatusUpdate(BaseModel):
    status: Literal["pending", "running", "succeeded", "failed"]


operations = {}


@app.post(
    "/operations", response_model=OperationResponse, status_code=status.HTTP_201_CREATED
)
def create_operation(operation: OperationCreate):
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "service_name": operation.service_name,
        "failure_type": operation.failure_type,
        "status": "pending",
    }
    operations[record_id] = record
    return record


@app.get("/operations/{operation_id}", response_model=OperationResponse)
def get_operation(operation_id: str):
    if operation_id in operations:
        return operations[operation_id]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found"
    )


@app.get("/operations", response_model=list[OperationResponse])
def get_operations():
    return list(operations.values())


@app.patch("/operations/{operation_id}", response_model=OperationResponse)
def update_operation(operation_id: str, body: OperationStatusUpdate):
    if operation_id not in operations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"operation {operation_id} does not exist!"
        )

    record = operations[operation_id]

    current_status = record["status"]
    requested_status = body.status

    allowed_next = ALLOWED_TRANSITIONS.get(current_status, [])
    if requested_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Transition from '{current_status}' "
                f"to '{requested_status}' is not allowed"
            )
        )

    record["status"] = requested_status
    return record
