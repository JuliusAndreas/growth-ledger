from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

DATE = r"^\d{4}-\d{2}-\d{2}$"
MONTH = r"^\d{4}-\d{2}$"


class _Doc(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Medium(_Doc):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field("", max_length=200)
    weight: float = Field(1, ge=0, le=5)
    order: int = 0
    archived: bool = False
    createdAt: str | None = None


class Entry(_Doc):
    mediumId: str = Field(min_length=1)
    date: str = Field(pattern=DATE)
    month: str = Field(pattern=MONTH)
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field("", max_length=5000)
    link: str = Field("", max_length=2000)
    depth: int = Field(ge=1, le=5)
    createdAt: str | None = None
    updatedAt: str | None = None

    @model_validator(mode="after")
    def month_matches_date(self):
        if self.date[:7] != self.month:
            raise ValueError("month must be the YYYY-MM part of date")
        return self


class Month(_Doc):
    score: int | None = Field(None, ge=0, le=100)
    mediums: list[dict[str, Any]] = []
    finalizedAt: str | None = None


MODELS: dict[str, type[_Doc]] = {"mediums": Medium, "entries": Entry, "months": Month}

# Minimum role needed to write each collection.
WRITE_ROLE = {"mediums": "admin", "entries": "user", "months": "user"}


class LoginIn(BaseModel):
    username: str
    password: str
