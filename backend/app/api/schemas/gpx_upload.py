from __future__ import annotations

import uuid

from pydantic import BaseModel
from pydantic import ConfigDict

from app.domain.route import Provenance
from app.domain.route import Publication


class GpxUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    publication: Publication
    provenance: Provenance
