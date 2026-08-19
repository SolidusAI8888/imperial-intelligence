from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CandidateExperience:
    persona_id: str
    dynasty: str
    evidence_ids: tuple[str, ...]
    experience_similarity: float
    evidence_strength: float
    stage_relevance: float
    lesson_clarity: float
    transferability: float
    counterevidence_quality: float
    rationale: str


@dataclass(frozen=True)
class CandidateScore:
    persona_id: str
    dynasty: str
    total_score: float
    evidence_ids: tuple[str, ...]
    rationale: str


_WEIGHTS = {
    "experience_similarity": 0.30,
    "evidence_strength": 0.20,
    "stage_relevance": 0.15,
    "lesson_clarity": 0.15,
    "transferability": 0.15,
    "counterevidence_quality": 0.05,
}


def score_candidate(candidate: CandidateExperience) -> CandidateScore:
    total = (
        candidate.experience_similarity * _WEIGHTS["experience_similarity"]
        + candidate.evidence_strength * _WEIGHTS["evidence_strength"]
        + candidate.stage_relevance * _WEIGHTS["stage_relevance"]
        + candidate.lesson_clarity * _WEIGHTS["lesson_clarity"]
        + candidate.transferability * _WEIGHTS["transferability"]
        + candidate.counterevidence_quality * _WEIGHTS["counterevidence_quality"]
    )
    return CandidateScore(
        persona_id=candidate.persona_id,
        dynasty=candidate.dynasty,
        total_score=round(total, 4),
        evidence_ids=candidate.evidence_ids,
        rationale=candidate.rationale,
    )


def rank_candidates(candidates: Iterable[CandidateExperience]) -> list[CandidateScore]:
    ranked = [score_candidate(candidate) for candidate in candidates]
    return sorted(ranked, key=lambda item: (-item.total_score, item.persona_id))


def select_best_candidate(candidates: Iterable[CandidateExperience]) -> CandidateScore:
    ranked = rank_candidates(candidates)
    if not ranked:
        raise ValueError("No eligible historical candidates")
    return ranked[0]


def first_fate_question_candidates() -> list[CandidateExperience]:
    """Reviewed MVP candidates for Q-FATE-AGENCY-001.

    Scores are intentionally explicit and deterministic for V1. They are not fame
    scores; each dimension describes the reviewed experience package currently
    available for the question. As more HER/HEU packages are reviewed, these
    values should be loaded from data rather than expanded here.
    """

    return [
        CandidateExperience(
            persona_id="liu_bang",
            dynasty="han",
            evidence_ids=(
                "CN-HAN-0001-V008-P0009",
                "CN-HAN-0001-V008-P0010",
                "CN-HAN-0001-V008-P0011",
            ),
            experience_similarity=0.88,
            evidence_strength=0.86,
            stage_relevance=0.90,
            lesson_clarity=0.76,
            transferability=0.78,
            counterevidence_quality=0.65,
            rationale=(
                "刘邦从基层吏员到秦末起事、受挫后再聚兵，直接经历个人处境被时代剧变重塑；"
                "其经历对‘外部条件与个人应对’高度相关，但现阶段可审核的自我反思材料少于唐太宗。"
            ),
        ),
        CandidateExperience(
            persona_id="tang_taizong",
            dynasty="tang",
            evidence_ids=(
                "CN-TANG-0001-V002-P0004",
                "CN-TANG-0002-V002-P0004",
                "CN-TANG-0004-V001-P0003",
                "CN-TANG-0004-V001-P0010",
                "CN-TANG-0004-V001-P0013",
                "CN-TANG-0004-V001-P0014",
            ),
            experience_similarity=0.94,
            evidence_strength=0.95,
            stage_relevance=0.95,
            lesson_clarity=0.96,
            transferability=0.89,
            counterevidence_quality=0.82,
            rationale=(
                "唐太宗既有隋末创业期的亲历，又有贞观时期对草创、守成、兼听、克终的明确反思，"
                "当前证据链同时覆盖处境变化、持续选择与纠错，因此与本题结构最完整。"
            ),
        ),
        CandidateExperience(
            persona_id="song_taizu",
            dynasty="song",
            evidence_ids=(
                "CN-SONG-0001-V001-P0004",
                "CN-SONG-0001-V001-P0005",
                "CN-SONG-0001-V001-P0010",
            ),
            experience_similarity=0.87,
            evidence_strength=0.84,
            stage_relevance=0.91,
            lesson_clarity=0.72,
            transferability=0.76,
            counterevidence_quality=0.62,
            rationale=(
                "赵匡胤从漫游无所遇、从军建功到陈桥即位，人生阶段变化极大，"
                "对‘时代机会与个人行动’有直接可比性；但当前正式知识层中的反思型 HEU 尚未达到唐太宗的密度。"
            ),
        ),
    ]
