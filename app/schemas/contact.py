from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    subject: str = Field(..., min_length=1, max_length=200)
    order_id: Optional[str] = Field(default=None, max_length=50)
    message: str = Field(..., min_length=10, max_length=4000)


class ContactResponse(BaseModel):
    message: str
