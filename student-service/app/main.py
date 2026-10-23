import os
from typing import List

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

if not JWT_SECRET or JWT_SECRET.startswith("change-me"):
    raise RuntimeError("Set a real JWT_SECRET in the .env file (see .env.example).")

# Table creation script: creates the tables on startup if they do not exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Service", version="1.0.0", description="CRUD operations for student records.")
bearer_scheme = HTTPBearer()


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Validate the JWT issued by the auth service (shared secret)."""
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_student_or_404(db: Session, student_id: int) -> models.Student:
    student = db.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Student {student_id} not found")
    return student


@app.get("/health", tags=["health"])
def health():
    return {"service": "student-service", "status": "ok"}


@app.post("/students", response_model=schemas.StudentOut, status_code=status.HTTP_201_CREATED, tags=["students"])
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db), _: dict = Depends(require_auth)):
    email = payload.email.lower()
    if db.query(models.Student).filter(models.Student.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "A student with this email already exists")
    data = payload.model_dump()
    data["email"] = email
    student = models.Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.get("/students", response_model=List[schemas.StudentOut], tags=["students"])
def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return db.query(models.Student).order_by(models.Student.id).offset(skip).limit(limit).all()


@app.get("/students/{student_id}", response_model=schemas.StudentOut, tags=["students"])
def get_student(student_id: int, db: Session = Depends(get_db), _: dict = Depends(require_auth)):
    return get_student_or_404(db, student_id)


@app.put("/students/{student_id}", response_model=schemas.StudentOut, tags=["students"])
def update_student(
    student_id: int,
    payload: schemas.StudentUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    student = get_student_or_404(db, student_id)
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        changes["email"] = changes["email"].lower()
        clash = (
            db.query(models.Student)
            .filter(models.Student.email == changes["email"], models.Student.id != student_id)
            .first()
        )
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, "A student with this email already exists")
    for field, value in changes.items():
        if value is not None:
            setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["students"])
def delete_student(student_id: int, db: Session = Depends(get_db), _: dict = Depends(require_auth)):
    student = get_student_or_404(db, student_id)
    db.delete(student)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
