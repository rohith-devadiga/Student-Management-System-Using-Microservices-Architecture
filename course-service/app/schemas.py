from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CourseBase(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    credits: int = Field(default=3, ge=1, le=10)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    credits: Optional[int] = Field(default=None, ge=1, le=10)


class CourseOut(CourseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class EnrollRequest(BaseModel):
    student_id: int = Field(ge=1)


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    student_id: int
    enrolled_at: datetime


class EnrolledStudents(BaseModel):
    course_id: int
    total: int
    students: List[Dict[str, Any]]
