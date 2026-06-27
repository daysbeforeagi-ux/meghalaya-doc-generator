from src.intake.models import Session, CreateSessionRequest, Speaker


def build_session_from_request(req: CreateSessionRequest) -> Session:
    """Convert validated Q1–Q5 intake answers into a Session object (§3, §5)."""
    speaker = Speaker(
        role=req.speaker_role,
        name=req.speaker_name,
    ) if req.speaker_role else None

    return Session(
        speaker=speaker,
        brief=req.brief,
        length_target=req.length_target,
    )
