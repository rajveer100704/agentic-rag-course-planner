"""
test_queries.py — 25-query evaluation set for the RAG assistant.

Categories:
  A) 10 Prerequisite checks (eligible / not eligible)
  B)  5 Prerequisite chain questions (multi-hop)
  C)  5 Program requirement questions
  D)  5 "Not in docs" / trick questions
"""

from typing import List, Dict, Any


def get_test_queries() -> List[Dict[str, Any]]:
    return [

        # ═══════════════════════════════════════════════
        # CATEGORY A: Prerequisite Checks (10 queries)
        # ═══════════════════════════════════════════════

        {
            "id": "A01",
            "category": "prereq_check",
            "query": "Can I take CS 201 if I've completed CS 101 with a B+?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS101": "B+"},
                "target_term": "Spring 2025"
            },
            "expected_decision": "ELIGIBLE",
            "rubric": "CS 201 requires CS 101 with C or higher. B+ satisfies this. Must cite CS 201 section.",
            "expected_citations": ["CS 201", "Object-Oriented Programming"],
            "expects_abstain": False
        },

        {
            "id": "A02",
            "category": "prereq_check",
            "query": "Can I take CS 250 if I have CS 201 with a C- and CS 150 with a B?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS201": "C-", "CS150": "B"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "CS 250 requires CS 201 with C or higher. C- does NOT satisfy 'C or higher' per policy. Must cite both CS 250 and academic policy (C- clarification).",
            "expected_citations": ["CS 250", "Grading Scale"],
            "expects_abstain": False
        },

        {
            "id": "A03",
            "category": "prereq_check",
            "query": "Am I eligible for CS 310 with CS 201 B and CS 250 A?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS201": "B", "CS250": "A"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "ELIGIBLE",
            "rubric": "CS 310 requires CS 201 C+ and CS 250 C+. Both satisfied. Must cite CS 310 section.",
            "expected_citations": ["CS 310", "Database Systems"],
            "expects_abstain": False
        },

        {
            "id": "A04",
            "category": "prereq_check",
            "query": "Can I enroll in CS 311 if I completed CS 210 with a C and CS 250 with a B-?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS210": "C", "CS250": "B-"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "ELIGIBLE",
            "rubric": "CS 311 requires CS 210 C+ and CS 250 C+. C meets 'C or higher'. B- meets 'C or higher'. Eligible.",
            "expected_citations": ["CS 311", "Operating Systems"],
            "expects_abstain": False
        },

        {
            "id": "A05",
            "category": "prereq_check",
            "query": "I have CS 250 with a B, CS 260 with a C, CS 220 with a D+. Can I take CS 320?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS250": "B", "CS260": "C", "CS220": "D+"},
                "target_term": "Spring 2025"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "CS 320 requires CS 220 with C or higher. D+ does NOT meet this. Must flag CS 220 failure and cite CS 320 prerequisites.",
            "expected_citations": ["CS 320", "Machine Learning"],
            "expects_abstain": False
        },

        {
            "id": "A06",
            "category": "prereq_check",
            "query": "Can I take CS 440 with CS 240 A- and CS 311 B?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS240": "A-", "CS311": "B"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "ELIGIBLE",
            "rubric": "CS 440 requires CS 240 C+ and CS 311 C+. Both met. Must cite CS 440 section.",
            "expected_citations": ["CS 440", "Advanced Cybersecurity"],
            "expects_abstain": False
        },

        {
            "id": "A07",
            "category": "prereq_check",
            "query": "I want to take CS 150. I've completed MATH 110 with a C-. Am I eligible?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"MATH110": "C-"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "CS 150 requires MATH 110 with C or higher. C- does not satisfy this. Must cite both CS 150 prereq and policy on C- not meeting C requirement.",
            "expected_citations": ["CS 150", "Grading Scale"],
            "expects_abstain": False
        },

        {
            "id": "A08",
            "category": "prereq_check",
            "query": "Can I take CS 490 Capstone? I have 92 credits, CS 301 with a B, and senior standing.",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS301": "B"},
                "credit_hours_earned": 92,
                "target_term": "Fall 2025"
            },
            "expected_decision": "ELIGIBLE",
            "rubric": "CS 490 requires 90+ credits, CS 301 C+, and senior standing. All met. Instructor consent also noted in catalog — must flag this.",
            "expected_citations": ["CS 490", "Senior Capstone"],
            "expects_abstain": False
        },

        {
            "id": "A09",
            "category": "prereq_check",
            "query": "I have no prerequisites done. Can I take CS 101?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Fall 2025"
            },
            "expected_decision": "ELIGIBLE",
            "rubric": "CS 101 has no prerequisites. Open enrollment. Must cite CS 101 section.",
            "expected_citations": ["CS 101", "Introduction to Programming"],
            "expects_abstain": False
        },

        {
            "id": "A10",
            "category": "prereq_check",
            "query": "Can I take CS 380 Compiler Design? I have CS 250 with a B+ but haven't taken CS 350.",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS250": "B+"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "CS 380 requires CS 250 AND CS 350. CS 350 is missing. NOT ELIGIBLE. Must cite CS 380 section and note CS 350 is the missing prereq.",
            "expected_citations": ["CS 380", "Compiler Design"],
            "expects_abstain": False
        },

        # ═══════════════════════════════════════════════
        # CATEGORY B: Multi-hop Chain Questions (5)
        # ═══════════════════════════════════════════════

        {
            "id": "B01",
            "category": "prereq_chain",
            "query": "What do I need to take CS 420 Deep Learning from scratch? I have only MATH 120.",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"MATH120": "A"},
                "target_term": "Fall 2026"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "CS 420 → CS 320 → CS 250 + CS 260 + CS 220. Also: CS 250 → CS 201 + CS 150. Must show full chain. With only MATH 120, need: CS 101, CS 150, CS 201, CS 210 (for other core), CS 220, CS 260 (from MATH 120), then CS 250, then CS 320, then CS 420. At minimum 5-6 semesters of prerequisites. Must cite all relevant course sections.",
            "expected_citations": ["CS 420", "CS 320", "CS 250"],
            "expects_abstain": False,
            "requires_multi_hop": True
        },

        {
            "id": "B02",
            "category": "prereq_chain",
            "query": "What is the full prerequisite chain for CS 411 Distributed Systems?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Spring 2025"
            },
            "expected_decision": "NEED MORE INFO",
            "rubric": "CS 411 → CS 311 + CS 340. CS 311 → CS 210 + CS 250. CS 340 → CS 210 + CS 250. CS 250 → CS 201 + CS 150. CS 210 → CS 101. CS 201 → CS 101. Chain: CS 101 → CS 201 + CS 210 → CS 250 (+ CS 150) → CS 311 + CS 340 → CS 411. Must cite each step.",
            "expected_citations": ["CS 411", "CS 311", "CS 340", "CS 250"],
            "expects_abstain": False,
            "requires_multi_hop": True
        },

        {
            "id": "B03",
            "category": "prereq_chain",
            "query": "I completed CS 101 B and MATH 120 A. How many semesters until I can take CS 320 Machine Learning?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS101": "B", "MATH120": "A"},
                "target_term": "Spring 2025"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "Need: CS 201 (have CS 101 ✓), CS 150 (need MATH 110/placement ✓ via MATH120), CS 260 (have MATH120 ✓), CS 220 (have MATH120 ✓), then CS 250 (need CS 201 + CS 150), then CS 320 (need CS 250 + CS 260 + CS 220). Roughly 3 semesters minimum. Must show chain reasoning with citations.",
            "expected_citations": ["CS 320", "CS 250", "CS 201"],
            "expects_abstain": False,
            "requires_multi_hop": True
        },

        {
            "id": "B04",
            "category": "prereq_chain",
            "query": "Can I take DS 301 Applied Machine Learning? I have DS 101, CS 220 B, and CS 260 C.",
            "profile": {
                "major": "B.S. Data Science",
                "completed_courses": {"DS101": "B", "CS220": "B", "CS260": "C"},
                "target_term": "Fall 2025"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "DS 301 requires DS 201 C+ + CS 220 C+ + CS 260 C+. DS 201 is MISSING (only have DS 101). CS 220 B ✓. CS 260 C ✓. Must flag DS 201 as missing. Must cite DS 301 section.",
            "expected_citations": ["DS 301", "Applied Machine Learning"],
            "expects_abstain": False,
            "requires_multi_hop": True
        },

        {
            "id": "B05",
            "category": "prereq_chain",
            "query": "What do I need before the Cybersecurity Certificate's hardest course, CS 440?",
            "profile": {
                "major": "Cybersecurity Certificate",
                "completed_courses": {"CS101": "A"},
                "target_term": "Fall 2026"
            },
            "expected_decision": "NOT ELIGIBLE",
            "rubric": "CS 440 → CS 240 + CS 311. CS 311 → CS 210 + CS 250. CS 250 → CS 201 + CS 150. CS 210 → CS 101 ✓. CS 240 → CS 101 ✓. Chain from CS 101: need CS 210, CS 201, CS 150, CS 250, CS 311, CS 240, then CS 440. Must show chain and cite all sections.",
            "expected_citations": ["CS 440", "CS 311", "CS 240", "CS 250"],
            "expects_abstain": False,
            "requires_multi_hop": True
        },

        # ═══════════════════════════════════════════════
        # CATEGORY C: Program Requirement Questions (5)
        # ═══════════════════════════════════════════════

        {
            "id": "C01",
            "category": "program_req",
            "query": "How many technical elective credits do I need for the B.S. in Computer Science?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Fall 2025"
            },
            "expected_decision": None,
            "rubric": "Answer: 15 elective credits, at least 9 at 300+ level, at most 6 from non-CS dept. Must cite B.S. CS Technical Electives section.",
            "expected_citations": ["Technical Electives", "B.S. Computer Science"],
            "expects_abstain": False
        },

        {
            "id": "C02",
            "category": "program_req",
            "query": "Does CS 390 Ethics count as both an ethics requirement and an elective?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS390": "A"},
                "target_term": "Spring 2025"
            },
            "expected_decision": None,
            "rubric": "Answer: CS 390 satisfies the Ethics Core AND the University Ethics Gen Ed requirement. It does NOT double-count toward Technical Electives. Must cite both the B.S. CS program page (Ethics requirement) and the Gen Ed section.",
            "expected_citations": ["CS 390", "Ethics", "General Education"],
            "expects_abstain": False
        },

        {
            "id": "C03",
            "category": "program_req",
            "query": "How many times can I repeat a required CS course if I fail it?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Fall 2025"
            },
            "expected_decision": None,
            "rubric": "Answer: Max 3 attempts total. A 4th attempt requires petition to Academic Standards Committee. Grade replacement policy: higher grade used in GPA. Must cite Course Repeat Policy section.",
            "expected_citations": ["Course Repeat Policy"],
            "expects_abstain": False
        },

        {
            "id": "C04",
            "category": "program_req",
            "query": "Can I count DS 301 as a technical elective for the B.S. Computer Science?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"DS301": "B"},
                "target_term": "Fall 2025"
            },
            "expected_decision": None,
            "rubric": "Answer: Yes. The B.S. CS program page explicitly lists DS 301 as an approved Technical Elective. Must cite the Technical Electives approved list.",
            "expected_citations": ["Technical Electives", "B.S. Computer Science"],
            "expects_abstain": False
        },

        {
            "id": "C05",
            "category": "program_req",
            "query": "I'm on academic probation. Can I enroll in 15 credits next semester?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Fall 2025",
                "on_probation": True
            },
            "expected_decision": None,
            "rubric": "Answer: No. Academic probation limits enrollment to 12 credits per term. Must cite Academic Probation Credit Limit section.",
            "expected_citations": ["Credit Load", "Academic Probation"],
            "expects_abstain": False
        },

        # ═══════════════════════════════════════════════
        # CATEGORY D: Not in Docs / Trick Questions (5)
        # ═══════════════════════════════════════════════

        {
            "id": "D01",
            "category": "not_in_docs",
            "query": "Is CS 310 offered this spring? Are there seats available?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS201": "A", "CS250": "B"},
                "target_term": "Spring 2025"
            },
            "expected_decision": "ABSTAIN",
            "rubric": "The catalog states CS 310 is offered Fall/Spring, but real-time seat availability is NOT in the catalog. Must abstain on seat availability and direct to Registrar's Schedule of Classes.",
            "expected_citations": [],
            "expects_abstain": True
        },

        {
            "id": "D02",
            "category": "not_in_docs",
            "query": "Who is the professor teaching CS 320 next semester?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Spring 2025"
            },
            "expected_decision": "ABSTAIN",
            "rubric": "Professor/instructor assignments are NOT in catalog documents. Must abstain and direct to department website or schedule of classes.",
            "expected_citations": [],
            "expects_abstain": True
        },

        {
            "id": "D03",
            "category": "not_in_docs",
            "query": "What's the exact passing percentage for CS 250 exams to get a C?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Fall 2025"
            },
            "expected_decision": "ABSTAIN",
            "rubric": "Specific exam grading breakdowns are NOT in the catalog (only letter-grade percentage ranges are given). Must abstain and direct to course syllabus.",
            "expected_citations": [],
            "expects_abstain": True
        },

        {
            "id": "D04",
            "category": "not_in_docs",
            "query": "Can my professor give me special permission to skip CS 250 entirely for CS 310?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {"CS201": "A"},
                "target_term": "Spring 2025"
            },
            "expected_decision": "NEED MORE INFO",
            "rubric": "The catalog states instructors may grant prerequisite overrides. However, whether a specific professor WILL grant this for CS 310 is NOT in the catalog. Must cite Prerequisite Override policy but abstain on the specific decision and refer to the instructor/department.",
            "expected_citations": ["Prerequisite Overrides"],
            "expects_abstain": True
        },

        {
            "id": "D05",
            "category": "not_in_docs",
            "query": "Is there a co-op or internship credit option that can substitute for electives in CS?",
            "profile": {
                "major": "B.S. Computer Science",
                "completed_courses": {},
                "target_term": "Fall 2025"
            },
            "expected_decision": "ABSTAIN",
            "rubric": "Co-op/internship credit substitution for electives is NOT mentioned in the provided catalog documents. Must abstain and direct to the CS advising office.",
            "expected_citations": [],
            "expects_abstain": True
        }
    ]


def evaluate_response(result: dict, test_case: dict) -> dict:
    """
    Rubric-based evaluation of a single response.
    Returns: {score, citation_present, decision_correct, abstain_correct, notes}
    """
    score = 0
    notes = []
    max_score = 10

    # 1. Citation coverage (3 pts)
    citations = result.get("citations", [])
    citation_text = " ".join(
        f"{c.get('section','')} {c.get('url','')}" for c in citations
    ).lower()
    has_citation = len(citations) > 0
    citation_score = 0
    expected_cit = test_case.get("expected_citations", [])
    if expected_cit:
        matches = sum(1 for ec in expected_cit
                      if any(ec.lower() in citation_text for _ in [1]))
        citation_score = min(3, round(3 * matches / len(expected_cit)))
        if not has_citation and not test_case.get("expects_abstain"):
            notes.append("FAIL: No citations provided for non-abstain response.")
    else:
        citation_score = 2 if test_case.get("expects_abstain") else 0
    score += citation_score

    # 2. Decision correctness (4 pts)
    expected_decision = test_case.get("expected_decision")
    actual_decision = result.get("overall_decision", result.get("response_type", "")).upper()
    decision_correct = False
    if expected_decision:
        if expected_decision.upper() in actual_decision:
            decision_correct = True
            score += 4
        elif test_case.get("expects_abstain") and "ABSTAIN" in actual_decision:
            decision_correct = True
            score += 4
        elif test_case.get("expects_abstain") and (
            "not in catalog" in result.get("answer", "").lower() or
            "don't have that information" in result.get("answer", "").lower()
        ):
            decision_correct = True
            score += 3
            notes.append("PARTIAL: Correct abstention but decision label unclear.")
        else:
            notes.append(f"FAIL: Expected {expected_decision}, got {actual_decision}")
    else:
        # No specific decision expected (program req / general)
        if result.get("answer"):
            score += 3
            decision_correct = True
        notes.append("No specific decision to evaluate; checking for grounded answer.")

    # 3. Abstention accuracy (2 pts)
    expects_abstain = test_case.get("expects_abstain", False)
    abstain_words = ["don't have that information", "not in the provided catalog",
                     "not in catalog", "contact your advisor", "schedule of classes"]
    answer = result.get("answer", "").lower()
    abstain_correct = not expects_abstain  # Default: no abstain needed
    if expects_abstain:
        if any(w in answer for w in abstain_words):
            abstain_correct = True
            score += 2
        else:
            notes.append("FAIL: Should have abstained but provided a guess.")
    else:
        if any(w in answer for w in abstain_words) and result.get("citations"):
            score += 1  # Has both answer and appropriate caution
            abstain_correct = True

    # 4. Audit passed (1 pt)
    if result.get("audit_passed", False):
        score += 1

    return {
        "test_id": test_case["id"],
        "category": test_case["category"],
        "score": score,
        "max_score": max_score,
        "pct": round(100 * score / max_score),
        "citation_present": has_citation,
        "citation_score": citation_score,
        "decision_correct": decision_correct,
        "abstain_correct": abstain_correct,
        "audit_passed": result.get("audit_passed", False),
        "confidence": result.get("confidence", "?"),
        "notes": notes
    }
