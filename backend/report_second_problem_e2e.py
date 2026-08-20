from app.services.cross_dynasty_selector import rank_candidates, problem_candidates
from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.problem_conversation_service import continue_problem_conversation


PROBLEM_ID = "Q-CAREER-PIVOT-001"


def main() -> None:
    ranked = rank_candidates(problem_candidates(PROBLEM_ID))
    answer = render_grounded_answer(PROBLEM_ID)
    followup = continue_problem_conversation(
        PROBLEM_ID,
        "你刚才说可以根据新信息修正决定，那怎么判断我是在理性调整，而不是因为受挫就逃避？",
        conversation_history=(answer.question, answer.historical_voice),
    )
    drift = continue_problem_conversation(
        PROBLEM_ID,
        "宋代财政制度是怎样设计的？",
        continuity_threshold=0.30,
    )

    print(f"problem_id={PROBLEM_ID}")
    print("ranking=" + ", ".join(f"{item.persona_id}:{item.total_score:.4f}" for item in ranked))
    print(f"selected_person={answer.person_id}")
    print(f"answer_status={answer.status}")
    print(f"followup_route={followup.route}")
    print(f"followup_person={followup.person_id}")
    print(f"drift_route={drift.route}")
    if drift.research_package is not None:
        print(f"drift_research_id={drift.research_package.proposed_problem_id}")
        print(f"drift_research_candidates={len(drift.research_package.candidates)}")


if __name__ == "__main__":
    main()
