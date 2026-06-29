from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class SystemSettingBase(BaseModel):
    key: str
    value: Any = None
    description: Optional[str] = None


class SystemSettingCreate(SystemSettingBase):
    pass


class SystemSettingUpdate(BaseModel):
    value: Any = None
    description: Optional[str] = None


class SystemSettingResponse(SystemSettingBase):
    id: UUID
    updated_at: datetime

    class Config:
        from_attributes = True
