from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


RecordStatus = Literal["draft", "reviewed", "accepted", "deprecated"]
KnowledgeStatus = Literal["draft", "reviewed", "accepted", "deprecated"]


class SourceReference(BaseModel):
    source_id: str
    canonical_ids: list[str] = Field(min_length=1)


class HistoricalRecord(BaseModel):
    """Factual, auditable historical record.

    HistoricalRecord is deliberately not a lesson or modern interpretation.
    It may represent a discussion, memorial, edict, event, appointment, battle,
    institutional record, or explicit reflection, provided every claim is
    traceable to Source Corpus evidence.
    """

    record_id: str = Field(pattern=r"^HER-[A-Z0-9-]+$")
    research_id: str
    title: str
    record_type: Literal[
        "discussion",
        "memorial",
        "edict",
        "event",
        "appointment",
        "battle",
        "institution",
        "reflection",
        "other",
    ]
    dynasty: str
    time_label: str | None = None
    participants: list[str] = Field(default_factory=list)
    historical_record: str
    sources: list[SourceReference] = Field(min_length=1)
    supported_claims: list[str] = Field(min_length=1)
    unsupported_claims: list[str] = Field(default_factory=list)
    derived_from_candidate_evidence_ids: list[str] = Field(default_factory=list)
    status: RecordStatus = "draft"

    @model_validator(mode="after")
    def require_canonical_traceability(self) -> "HistoricalRecord":
        canonical_ids = [cid for source in self.sources for cid in source.canonical_ids]
        if not canonical_ids:
            raise ValueError("HistoricalRecord requires at least one Source Corpus canonical ID")
        return self


class HistoricalExperienceUnit(BaseModel):
    """Person-centered lived experience derived only from Historical Records."""

    heu_id: str = Field(pattern=r"^HEU-[A-Z0-9-]+$")
    research_id: str
    title: str
    experience_owner: str
    record_links: list[str] = Field(min_length=1)
    challenge: str
    response_or_choice: list[str] = Field(min_length=1)
    experienced_outcome: list[str] = Field(min_length=1)
    explicit_reflection: list[str] = Field(default_factory=list)
    interpretation: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(min_length=1)
    status: KnowledgeStatus = "draft"

    @model_validator(mode="after")
    def validate_record_links(self) -> "HistoricalExperienceUnit":
        if any(not rid.startswith("HER-") for rid in self.record_links):
            raise ValueError("Every HEU record link must reference a HER object")
        return self


class Insight(BaseModel):
    """Transferable inference derived from HEUs, never directly from Source Corpus."""

    insight_id: str = Field(pattern=r"^INS-[A-Z0-9-]+$")
    research_id: str
    statement: str
    derived_from_heus: list[str] = Field(min_length=1)
    applies_when: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)
    status: KnowledgeStatus = "draft"

    @model_validator(mode="after")
    def validate_heu_links(self) -> "Insight":
        if any(not hid.startswith("HEU-") for hid in self.derived_from_heus):
            raise ValueError("Insight may derive only from HEU objects")
        return self


class RoleExperienceLink(BaseModel):
    person_id: str
    heu_id: str = Field(pattern=r"^HEU-[A-Z0-9-]+$")
    relation: Literal[
        "experience_owner",
        "decision_maker",
        "witness",
        "participant",
        "affected_party",
        "chronicler",
    ]
    responder_eligible: bool
    personal_experience_strength: Literal["none", "weak", "medium", "strong", "primary"]
    life_course_rule: Literal["full_lifetime"] = "full_lifetime"


class RuntimeContext(BaseModel):
    """Validated input consumed by persona answer generation.

    The context enforces the project's core rule that a historical persona
    answers from the perspective of their complete lifetime, while only using
    historically supported records, experiences and insights supplied here.
    """

    problem_id: str
    question: str
    person_id: str
    life_course_rule: Literal["full_lifetime"] = "full_lifetime"
    records: list[HistoricalRecord] = Field(min_length=1)
    experiences: list[HistoricalExperienceUnit] = Field(min_length=1)
    insights: list[Insight] = Field(min_length=1)
    role_links: list[RoleExperienceLink] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_chain(self) -> "RuntimeContext":
        record_ids = {record.record_id for record in self.records}
        heu_ids = {heu.heu_id for heu in self.experiences}

        for heu in self.experiences:
            missing = set(heu.record_links) - record_ids
            if missing:
                raise ValueError(f"HEU {heu.heu_id} references missing HER records: {sorted(missing)}")

        for insight in self.insights:
            missing = set(insight.derived_from_heus) - heu_ids
            if missing:
                raise ValueError(
                    f"Insight {insight.insight_id} references missing HEUs: {sorted(missing)}"
                )

        eligible_person_links = [
            link
            for link in self.role_links
            if link.person_id == self.person_id and link.responder_eligible
        ]
        if not eligible_person_links:
            raise ValueError("Selected responder must have at least one eligible RoleExperienceLink")

        missing_linked_heus = {
            link.heu_id for link in eligible_person_links if link.heu_id not in heu_ids
        }
        if missing_linked_heus:
            raise ValueError(
                f"Role links reference HEUs missing from RuntimeContext: {sorted(missing_linked_heus)}"
            )

        return self
