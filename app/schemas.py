from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from settings import TYPES


class MessageIn(BaseModel):
    dt_from: datetime
    dt_upto: datetime
    group_type: str

    @classmethod
    @field_validator("dt_from", "dt_upto")
    def date_validator(cls, v: str) -> datetime:
        return datetime.fromisoformat(v)

    @model_validator(mode="after")
    def validator(self) -> "MessageIn":
        if self.group_type in TYPES:
            return self
        return ValueError(f"Недопустимый тип агрегации: {' '.join(TYPES)}")
