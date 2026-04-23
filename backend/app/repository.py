from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import InteractionRecord, SampleDistribution
from .schemas import InteractionFormState


def _dump_list(items: list[str]) -> str:
    return json.dumps(items)


def _load_list(value: str) -> list[str]:
    if not value:
        return []
    return json.loads(value)


def save_interaction(db: Session, form_state: InteractionFormState) -> InteractionRecord:
    record = InteractionRecord(
        hcp_name=form_state.hcp_name or "Unknown HCP",
        interaction_type=form_state.interaction_type,
        interaction_date=form_state.date,
        interaction_time=form_state.time,
        attendees=_dump_list(form_state.attendees),
        topics_discussed=form_state.topics_discussed,
        materials_shared=_dump_list(form_state.materials_shared),
        sentiment=form_state.sentiment,
        outcomes=form_state.outcomes,
        follow_up_actions=form_state.follow_up_actions,
        ai_suggested_follow_ups=_dump_list(form_state.ai_suggested_follow_ups),
        compliance_notes=_dump_list(form_state.compliance_notes),
        samples=[
            SampleDistribution(sample_name=item.name, quantity=item.quantity)
            for item in form_state.samples_distributed
        ],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_interactions(db: Session) -> list[InteractionRecord]:
    statement = select(InteractionRecord).order_by(InteractionRecord.created_at.desc()).limit(20)
    return list(db.scalars(statement).all())


def record_to_form_state(record: InteractionRecord) -> InteractionFormState:
    return InteractionFormState(
        hcp_name=record.hcp_name,
        interaction_type=record.interaction_type,
        date=record.interaction_date,
        time=record.interaction_time,
        attendees=_load_list(record.attendees),
        topics_discussed=record.topics_discussed,
        materials_shared=_load_list(record.materials_shared),
        samples_distributed=[
            {"name": sample.sample_name, "quantity": sample.quantity}
            for sample in record.samples
        ],
        sentiment=record.sentiment,
        outcomes=record.outcomes,
        follow_up_actions=record.follow_up_actions,
        ai_suggested_follow_ups=_load_list(record.ai_suggested_follow_ups),
        compliance_notes=_load_list(record.compliance_notes),
    )
