import re

from app.services.problem_draft_package import build_problem_draft_package
from app.services.problem_research_package import provisional_problem_id


_DRAFT_ID_RE = re.compile(r"^Q-RESEARCH-[A-F0-9]{16}$")


def test_research_and_draft_ids_share_the_same_16_hex_contract(monkeypatch):
    monkeypatch.setattr(
        "app.services.problem_research_package.build_problem_insight_review_queue",
        lambda *args, **kwargs: [],
    )
    problem_id = provisional_problem_id("职业低谷时应该坚持还是改变？")
    assert _DRAFT_ID_RE.fullmatch(problem_id)

    package = build_problem_draft_package("职业低谷时应该坚持还是改变？")
    assert package.problem_id == problem_id
    assert _DRAFT_ID_RE.fullmatch(package.problem_id)
