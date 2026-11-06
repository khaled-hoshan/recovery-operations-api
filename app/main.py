import logging
import uuid
from datetime import datetime
from typing import Literal
from fastapi import FastAPI, status, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app import models


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


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
    id: uuid.UUID
    service_name: str
    failure_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationStatusUpdate(BaseModel):
    status: Literal["pending", "running", "succeeded", "failed"]


@app.post(
    "/operations", response_model=OperationResponse, status_code=status.HTTP_201_CREATED
)
def create_operation(operation: OperationCreate, db: Session = Depends(get_db)):
    db_operation = models.Operation(
        service_name=operation.service_name, failure_type=operation.failure_type
    )
    try:
        db.add(db_operation)
        db.commit()
        db.refresh(db_operation)
        logger.info(
            "operation_created operation_id=%s",
            db_operation.id,
        )
    except SQLAlchemyError as exc:
        logger.error(
            "database_operation_failed event=create_operation error_type=%s",
            type(exc).__name__,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating operation",
        )

    return db_operation


@app.get("/operations/{operation_id}", response_model=OperationResponse)
def get_operation(operation_id: uuid.UUID, db: Session = Depends(get_db)):
    operation = db.get(models.Operation, operation_id)

    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found"
        )
    return operation


@app.get("/operations", response_model=list[OperationResponse])
def get_operations(db: Session = Depends(get_db)):
    return db.query(models.Operation).all()


@app.patch("/operations/{operation_id}", response_model=OperationResponse)
def update_operation(
    operation_id: uuid.UUID, body: OperationStatusUpdate, db: Session = Depends(get_db)
):
    operation = db.get(models.Operation, operation_id)
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found",
        )

    current_status = operation.status
    requested_status = body.status

    allowed_next = ALLOWED_TRANSITIONS.get(current_status, [])
    if requested_status not in allowed_next:
        logger.warning(
            "operation_transition_rejected operation_id=%s from=%s to=%s",
            operation_id,
            current_status,
            requested_status,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Transition from '{current_status}' "
                f"to '{requested_status}' is not allowed"
            ),
        )

    operation.status = requested_status

    try:
        db.commit()
        db.refresh(operation)
        logger.info(
            "operation_status_changed operation_id=%s from=%s to=%s",
            operation_id,
            current_status,
            requested_status,
        )
    except SQLAlchemyError as exc:
        logger.error(
            "database_operation_failed event=update_operation error_type=%s",
            type(exc).__name__,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating operation",
        )

    return operation
