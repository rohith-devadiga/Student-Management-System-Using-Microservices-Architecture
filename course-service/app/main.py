import os
from typing import List

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
STUDENT_SERVICE_URL = os.getenv("STUDENT_SERVICE_URL", "http://localhost:8002").rstrip("/")

if not JWT_SECRET or JWT_SECRET.startswith("change-me"):
    raise RuntimeError("Set a real JWT_SECRET in the .env file (see .env.example).")

# Table creation script: creates the tables on startup if they do not exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Course Service",
    version="1.0.0",
    description="Course management and student enrollment.",
)
bearer_scheme = HTTPBearer()


def require_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """Validate the JWT issued by the auth service and return the raw token (forwarded to the student service)."""
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_course_or_404(db: Session, course_id: int) -> models.Course:
    course = db.get(models.Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Course {course_id} not found")
    return course


async def call_student_service(path: str, token: str) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            return await client.get(f"{STUDENT_SERVICE_URL}{path}", headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Student service is unavailable")


@app.get("/health", tags=["health"])
def health():
    return {"service": "course-service", "status": "ok"}


@app.post("/courses", response_model=schemas.CourseOut, status_code=status.HTTP_201_CREATED, tags=["courses"])
def create_course(payload: schemas.CourseCreate, db: Session = Depends(get_db), _: str = Depends(require_token)):
    code = payload.code.strip().upper()
    if db.query(models.Course).filter(models.Course.code == code).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "A course with this code already exists")
    data = payload.model_dump()
    data["code"] = code
    course = models.Course(**data)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.get("/courses", response_model=List[schemas.CourseOut], tags=["courses"])
def list_courses(db: Session = Depends(get_db), _: str = Depends(require_token)):
    return db.query(models.Course).order_by(models.Course.id).all()


@app.get("/courses/{course_id}", response_model=schemas.CourseOut, tags=["courses"])
def get_course(course_id: int, db: Session = Depends(get_db), _: str = Depends(require_token)):
    return get_course_or_404(db, course_id)


@app.put("/courses/{course_id}", response_model=schemas.CourseOut, tags=["courses"])
def update_course(
    course_id: int,
    payload: schemas.CourseUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_token),
):
    course = get_course_or_404(db, course_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("code"):
        changes["code"] = changes["code"].strip().upper()
        clash = (
            db.query(models.Course)
            .filter(models.Course.code == changes["code"], models.Course.id != course_id)
            .first()
        )
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, "A course with this code already exists")
    for field, value in changes.items():
        if value is not None or field == "description":
            setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@app.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["courses"])
def delete_course(course_id: int, db: Session = Depends(get_db), _: str = Depends(require_token)):
    course = get_course_or_404(db, course_id)
    db.delete(course)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Enrollment: assign courses to students / list students in a course ----


@app.post(
    "/courses/{course_id}/students",
    response_model=schemas.EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["enrollment"],
)
async def assign_student(
    course_id: int,
    payload: schemas.EnrollRequest,
    db: Session = Depends(get_db),
    token: str = Depends(require_token),
):
    get_course_or_404(db, course_id)

    response = await call_student_service(f"/students/{payload.student_id}", token)
    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Student {payload.student_id} not found")
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not verify the student")

    existing = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == course_id, models.Enrollment.student_id == payload.student_id)
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Student is already enrolled in this course")

    enrollment = models.Enrollment(course_id=course_id, student_id=payload.student_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@app.get("/courses/{course_id}/students", response_model=schemas.EnrolledStudents, tags=["enrollment"])
async def list_enrolled_students(
    course_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(require_token),
):
    get_course_or_404(db, course_id)
    student_ids = [
        row.student_id for row in db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id)
    ]
    if not student_ids:
        return {"course_id": course_id, "total": 0, "students": []}

    response = await call_student_service("/students", token)
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not load student details")
    wanted = set(student_ids)
    # Students deleted from the student service are skipped.
    students = [s for s in response.json() if s["id"] in wanted]
    return {"course_id": course_id, "total": len(students), "students": students}


@app.delete(
    "/courses/{course_id}/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["enrollment"],
)
def unassign_student(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_token),
):
    enrollment = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == course_id, models.Enrollment.student_id == student_id)
        .first()
    )
    if enrollment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrollment not found")
    db.delete(enrollment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
