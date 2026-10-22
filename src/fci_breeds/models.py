from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

INDEX_URL = "https://www.fci.be/en/nomenclature/"
MATRIX_URL = INDEX_URL + "varietes.aspx"
TRIAL_MEANINGS = {
    "": "Not marked as subject to a working trial",
    "*": "Subject to a working trial according to the FCI breeds nomenclature",
    "(*)": "Subject to a working trial only for the countries having applied for it",
    "(**)": "Subject to a working trial only for the Nordic countries (Finland, Norway, Sweden)",
}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Variety(Model):
    code: str | None = None
    label: str
    source_labels: list[str]
    size: str | None = None
    coat: str | None = None
    colors: list[str] = Field(default_factory=list)
    cacib_marker: str = ""
    cacib_group_id: str | None = None
    subvarieties: list["Variety"] = Field(default_factory=list)


class Breed(Model):
    fci_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    english_name: str | None = None
    group: int | None = Field(default=None, ge=1, le=10)
    group_name: str | None = None
    section: str | None = None
    country: str | None = None
    recognition_status: Literal["definitive", "provisional"]
    validity_date: date | None = None
    source_url: str
    varieties_source_url: str
    cacib_marker: str = ""
    cacib_group_id: str | None = None
    working_trial_marker: str = ""
    working_trial: str | None = None
    varieties: list[Variety] = Field(default_factory=list)


class Snapshot(Model):
    schema_version: Literal["1.0"] = "1.0"
    scraped_at: datetime
    source_urls: list[str]
    breeds: list[Breed]
