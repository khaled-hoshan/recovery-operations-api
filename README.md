# Recovery Operations API

A small REST API for recording and tracking recovery operations.

An external recovery system decides what to do when a distributed
application experiences a failure. This API records the operation,
tracks its status, and exposes the result to other components.

This project does not detect failures, diagnose them, or execute
recovery actions. It manages records associated with those actions.

## Skills Demonstrated

- API design with Python and FastAPI
- PostgreSQL and database integration
- Unit and API testing with pytest
- CI/CD with GitHub Actions
- Cloud deployment using AWS

