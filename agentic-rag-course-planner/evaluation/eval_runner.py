"""
eval_runner.py — Runs the full 25-query evaluation and produces:
  - Per-query results table
  - Aggregate metrics
  - 3 detailed transcripts (correct eligibility, course plan, abstention)
  - Summary report saved to outputs/evaluation_report.md
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents import StudentProfile, run_pipeline
from formatter import format_response
from evaluation.test_queries import get_test_queries, evaluate_response


def run_full_evaluation(store) -> None:
    test_cases = get_test_queries()
    all_results = []
    all_evals = []

    print("\n" + "=" * 70)
    print("RUNNING EVALUATION — 25 Queries")
    print("=" * 70)

    for tc in test_cases:
        print(f"  [{tc['id']}] {tc['query'][:60]}...")

        # Build profile
        profile_dict = tc.get("profile", {})
        profile = StudentProfile()
        profile.major = profile_dict.get("major", "B.S. Computer Science")
        profile.completed_courses = profile_dict.get("completed_courses", {})
        profile.target_term = profile_dict.get("target_term", "Fall 2025")
        profile.max_credits = profile_dict.get("max_credits", 18)
        profile.credit_hours_earned = profile_dict.get("credit_hours_earned", 0)
        profile.gpa = profile_dict.get("gpa", None)
        profile.on_probation = profile_dict.get("on_probation", False)

        result = run_pipeline(tc["query"], profile, store, verbose=False)
        formatted = format_response(result)
        eval_result = evaluate_response(result, tc)

        all_results.append({
            "test_case": tc,
            "pipeline_result": result,
            "formatted": formatted,
            "eval": eval_result
        })
        all_evals.append(eval_result)

        status = "✅" if eval_result["decision_correct"] else "❌"
        print(f"    {status} Score: {eval_result['score']}/{eval_result['max_score']} | "
              f"Cit: {'✓' if eval_result['citation_present'] else '✗'} | "
              f"Decision: {'✓' if eval_result['decision_correct'] else '✗'} | "
              f"Abstain: {'✓' if eval_result['abstain_correct'] else '✗'}")

    # ── Aggregate Metrics ────────────────────────────────────────
    cat_a = [e for e in all_evals if e["category"] == "prereq_check"]
    cat_b = [e for e in all_evals if e["category"] == "prereq_chain"]
    cat_c = [e for e in all_evals if e["category"] == "program_req"]
    cat_d = [e for e in all_evals if e["category"] == "not_in_docs"]

    def pct(lst, key):
        if not lst: return 0
        return round(100 * sum(1 for e in lst if e.get(key)) / len(lst))

    def avg_score(lst):
        if not lst: return 0
        return round(sum(e["score"] for e in lst) / sum(e["max_score"] for e in lst) * 100)

    report = []
    report.append("# RAG Prerequisite Assistant — Evaluation Report\n")
    report.append("## Aggregate Metrics\n")

    total_cit = pct(all_evals, "citation_present")
    total_dec = pct(all_evals, "decision_correct")
    total_abs = pct(all_evals, "abstain_correct")
    total_audit = pct(all_evals, "audit_passed")
    total_score = avg_score(all_evals)

    report.append(f"| Metric | Score |")
    report.append(f"|--------|-------|")
    report.append(f"| **Citation Coverage Rate** | {total_cit}% |")
    report.append(f"| **Eligibility Decision Accuracy (prereq checks)** | {pct(cat_a, 'decision_correct')}% |")
    report.append(f"| **Prerequisite Chain Accuracy** | {pct(cat_b, 'decision_correct')}% |")
    report.append(f"| **Program Requirement Accuracy** | {pct(cat_c, 'decision_correct')}% |")
    report.append(f"| **Abstention Accuracy (not-in-docs)** | {pct(cat_d, 'abstain_correct')}% |")
    report.append(f"| **Audit Pass Rate** | {total_audit}% |")
    report.append(f"| **Overall Score** | {total_score}% |\n")

    # ── Per-Query Table ─────────────────────────────────────────
    report.append("## Per-Query Results\n")
    report.append("| ID | Category | Score | Cited | Decision✓ | Abstain✓ | Notes |")
    report.append("|----|----------|-------|-------|-----------|----------|-------|")
    for e in all_evals:
        notes_short = "; ".join(e["notes"])[:60] if e["notes"] else "—"
        report.append(
            f"| {e['test_id']} | {e['category']} | {e['score']}/{e['max_score']} "
            f"| {'✓' if e['citation_present'] else '✗'} "
            f"| {'✓' if e['decision_correct'] else '✗'} "
            f"| {'✓' if e['abstain_correct'] else '✗'} "
            f"| {notes_short} |"
        )

    # ── Rubric Description ───────────────────────────────────────
    report.append("\n## Rubric\n")
    report.append("""
Each query is scored out of 10 points:
- **Citation Score (0–3)**: Does the response cite catalog sources? Do citations match expected sections?
- **Decision Correctness (0–4)**: Does ELIGIBLE/NOT ELIGIBLE/ABSTAIN match the ground truth?
- **Abstention Accuracy (0–2)**: For "not in docs" queries, does the system correctly abstain rather than guess?
- **Audit Pass (0–1)**: Did the internal VerifierAgent flag no major issues?

Grades: ≥80% = Excellent, 70–79% = Good, 60–69% = Needs Improvement, <60% = Poor.
""")

    # ── 3 Detailed Transcripts ───────────────────────────────────
    report.append("\n---\n## Transcript 1: Correct Eligibility Decision with Citations")
    # Find best-scoring prereq_check
    prereq_results = [r for r in all_results if r["test_case"]["category"] == "prereq_check"
                      and r["eval"]["decision_correct"]]
    if prereq_results:
        t1 = prereq_results[0]
        report.append(f"\n**Query ({t1['test_case']['id']}):** {t1['test_case']['query']}")
        report.append(f"\n**Profile:** {json.dumps(t1['test_case']['profile'], indent=2)}")
        report.append(f"\n**Response:**\n```\n{t1['formatted'][:2000]}\n```")
        report.append(f"\n**Rubric:** {t1['test_case']['rubric']}")
        report.append(f"\n**Evaluation:** Score {t1['eval']['score']}/10 | Decision: {'✓' if t1['eval']['decision_correct'] else '✗'}")

    report.append("\n---\n## Transcript 2: Course Plan Output with Justification + Citations")
    # Find a plan result (use a prereq check with CS 301 eligible as demo)
    plan_demo_profile = StudentProfile()
    plan_demo_profile.major = "B.S. Computer Science"
    plan_demo_profile.completed_courses = {
        "CS101": "A", "CS150": "B+", "MATH120": "A-", "CS201": "B"
    }
    plan_demo_profile.target_term = "Fall 2025"
    plan_result = run_pipeline(
        "Plan my courses for Fall 2025. I'm in B.S. Computer Science.",
        plan_demo_profile, store
    )
    plan_formatted = format_response(plan_result)
    report.append(f"\n**Query:** Plan my courses for Fall 2025. I'm in B.S. Computer Science.")
    report.append(f"\n**Profile:** CS101:A, CS150:B+, MATH120:A-, CS201:B")
    report.append(f"\n**Response:**\n```\n{plan_formatted[:2500]}\n```")

    report.append("\n---\n## Transcript 3: Correct Abstention + Guidance")
    abstain_results = [r for r in all_results if r["test_case"]["category"] == "not_in_docs"
                       and r["eval"]["abstain_correct"]]
    if abstain_results:
        t3 = abstain_results[0]
        report.append(f"\n**Query ({t3['test_case']['id']}):** {t3['test_case']['query']}")
        report.append(f"\n**Response:**\n```\n{t3['formatted'][:1500]}\n```")
        report.append(f"\n**Rubric:** {t3['test_case']['rubric']}")
        report.append(f"\n**Evaluation:** Correct abstention | Score {t3['eval']['score']}/10")

    report_text = "\n".join(report)

    # Save report
    out_path = Path(__file__).parent.parent / "outputs" / "evaluation_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_text, encoding="utf-8")
    print(f"\n✅ Evaluation complete! Report saved to {out_path}")

    # Print summary to console
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Citation Coverage Rate:              {total_cit}%")
    print(f"  Prereq Check Decision Accuracy:      {pct(cat_a, 'decision_correct')}%")
    print(f"  Prereq Chain Decision Accuracy:      {pct(cat_b, 'decision_correct')}%")
    print(f"  Program Requirement Accuracy:        {pct(cat_c, 'decision_correct')}%")
    print(f"  Abstention Accuracy (not-in-docs):   {pct(cat_d, 'abstain_correct')}%")
    print(f"  Audit Pass Rate:                     {total_audit}%")
    print(f"  OVERALL SCORE:                       {total_score}%")
    print("=" * 70)

    return all_results, all_evals
