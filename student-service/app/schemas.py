from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

PHONE_PATTERN = r"^\+?[0-9][0-9\- ]{6,18}$"


class StudentBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(pattern=PHONE_PATTERN, description="Digits, optional leading +, spaces or dashes")
    department: str = Field(min_length=2, max_length=100)
    course: str = Field(min_length=2, max_length=100)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    department: Optional[str] = Field(default=None, min_length=2, max_length=100)
    course: Optional[str] = Field(default=None, min_length=2, max_length=100)


class StudentOut(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
