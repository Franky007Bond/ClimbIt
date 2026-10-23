from pydantic import BaseModel, ConfigDict, model_validator


class DescriptiveEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_revision_number: int
    description: str | None = None
    season_note: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> DescriptiveEditRequest:
        descriptive_fields = self.model_fields_set - {"base_revision_number"}
        if not descriptive_fields:
            raise ValueError("at least one of description or season_note is required")
        return self


class DescriptiveEditResponse(BaseModel):
    revision_number: int
    description: str
    season_note: str | None
