from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    speech = "speech"
    press_release = "press_release"


class SpeakerRole(str, Enum):
    cm = "cm"
    governor = "governor"
    deputy_cm = "deputy_cm"
    other = "other"


class SessionStatus(str, Enum):
    intake = "intake"
    researching = "researching"
    drafting = "drafting"
    review = "review"
    done = "done"
    error = "error"


class LengthTarget(str, Enum):
    w100_150 = "100-150"
    w150_500 = "150-500"
    w500_750 = "500-750"
    w750_1250 = "750-1250"
    w1250_plus = "1250+"
    quality_based = "quality-based"


class SpeakerInfo(BaseModel):
    role: SpeakerRole
    name: Optional[str] = None
    researched_context: Optional[str] = None


class PressOptions(BaseModel):
    use_pictures: bool = False
    image_refs: list[str] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    claim_id: str
    claim: str
    supporting_passage: str
    source_url: str
    source_tier: Literal[1, 2, 3]
    publisher: str
    accessed_at: datetime
    confidence: Literal["high", "medium", "flagged"]


class Session(BaseModel):
    session_id: str
    created_at: datetime
    doc_type: Optional[DocType] = None
    speaker: Optional[SpeakerInfo] = None
    press_options: Optional[PressOptions] = None
    brief: Optional[str] = None
    length_target: Optional[LengthTarget] = None
    uploads: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    style_profile_ref: Optional[str] = None
    status: SessionStatus = SessionStatus.intake
    error_message: Optional[str] = None
    deliverable_path: Optional[str] = None
    dossier_path: Optional[str] = None


class IntakePayload(BaseModel):
    doc_type: Optional[DocType] = None
    speaker_role: Optional[SpeakerRole] = None
    speaker_name: Optional[str] = None
    use_pictures: Optional[bool] = None
    brief: Optional[str] = None
    length_target: Optional[LengthTarget] = None


class SessionPublic(BaseModel):
    session_id: str
    status: SessionStatus
    doc_type: Optional[DocType] = None
    brief: Optional[str] = None
    length_target: Optional[LengthTarget] = None
    error_message: Optional[str] = None
    deliverable_ready: bool = False
    dossier_ready: bool = False
