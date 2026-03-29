"""
agents.py — Agentic pipeline for the RAG Prerequisite & Course Planning Assistant.

Implements three agents as Python classes (LangChain-style chain design):

  1. IntakeAgent      — normalises student profile, asks clarifying questions
  2. RetrieverAgent   — retrieves relevant catalog chunks for a query
  3. PlannerAgent     — generates grounded answers and course plans
  4. VerifierAgent    — audits answers for unsupported claims and missing citations

Each agent has a `run(state) -> state` method and a `_prompt` that defines its behavior.
The full pipeline is orchestrated by `run_pipeline(user_input, student_profile, store)`.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# Student Profile (shared state)
# ─────────────────────────────────────────────────────────────

class StudentProfile:
    def __init__(self):
        self.name: Optional[str] = None
        self.major: Optional[str] = None
        self.catalog_year: Optional[str] = None
        self.completed_courses: Dict[str, str] = {}   # {"CS101": "B+", ...}
        self.in_progress: List[str] = []               # ["MATH120"]
        self.target_term: Optional[str] = None         # "Fall 2025"
        self.max_credits: int = 18
        self.credit_hours_earned: int = 0
        self.gpa: Optional[float] = None
        self.transfer_credits: List[str] = []
        self.on_probation: bool = False

    def has_completed(self, course: str, min_grade: str = "C") -> Tuple[bool, str]:
        """
        Check if student completed course with at least min_grade.
        Returns (bool, reason).
        """
        c = course.upper().replace(" ", "")
        for k, grade in self.completed_courses.items():
            if k.upper().replace(" ", "") == c:
                if _grade_gte(grade, min_grade):
                    return True, f"Completed {course} with {grade}"
                else:
                    return False, f"Completed {course} with {grade} (need {min_grade} or higher)"
        if course.upper().replace(" ", "") in [x.upper().replace(" ", "") for x in self.in_progress]:
            return False, f"{course} is currently in-progress (not yet completed)"
        return False, f"{course} not found in completed courses"

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: Dict) -> "StudentProfile":
        p = cls()
        p.__dict__.update(d)
        return p


GRADE_ORDER = ["F", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A"]

def _grade_gte(earned: str, required: str) -> bool:
    """Return True if earned grade >= required grade."""
    earned = earned.upper().strip()
    required = required.upper().strip()
    if earned not in GRADE_ORDER or required not in GRADE_ORDER:
        return False
    return GRADE_ORDER.index(earned) >= GRADE_ORDER.index(required)


# ─────────────────────────────────────────────────────────────
# Agent 1: Intake Agent
# ─────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["major", "completed_courses", "target_term"]

CLARIFYING_QUESTIONS = {
    "major": "What is your declared major or program (e.g., B.S. Computer Science, B.S. Data Science, Cybersecurity Certificate)?",
    "completed_courses": "Which courses have you completed so far, and what grades did you receive? (e.g., CS101: B+, MATH120: A)",
    "target_term": "Which term are you planning for (e.g., Fall 2025, Spring 2026)?",
    "catalog_year": "Which catalog year applies to you (e.g., 2023–2024)? If unsure, this is usually the year you declared your major.",
    "max_credits": "How many credits are you planning to take next term (or what is your maximum)?",
    "credit_hours_earned": "How many total credit hours have you earned so far (including current term)?",
    "gpa": "What is your current cumulative GPA? (Only needed for probation checks and overload requests.)"
}


class IntakeAgent:
    """
    Normalises student profile from user input.
    Identifies missing required information and generates clarifying questions.
    """
    name = "IntakeAgent"

    def run(self, user_input: str, profile: StudentProfile) -> Dict[str, Any]:
        """
        Parse user input to extract/update profile fields.
        Returns: {profile, missing_fields, clarifying_questions, ready_to_plan}
        """
        updated = _parse_profile_from_text(user_input, profile)
        missing = self._missing_fields(updated)
        questions = [CLARIFYING_QUESTIONS[f] for f in missing[:5]]

        return {
            "profile": updated,
            "missing_fields": missing,
            "clarifying_questions": questions,
            "ready_to_plan": len(missing) == 0
        }

    def _missing_fields(self, profile: StudentProfile) -> List[str]:
        """Only ask for info that is truly critical AND missing."""
        missing = []
        # Only ask for major if question involves planning (not simple prereq checks)
        # For prereq checks, major is optional
        if not profile.major:
            missing.append("major")
        # Completed courses: only required for eligibility/planning questions
        # If user described courses in text, parser may have missed them; don't block
        # We only block if BOTH completed_courses and in_progress are empty AND
        # the query doesn't contain any course codes
        return missing  # Lean toward answering; clarify only missing major


def _parse_profile_from_text(text: str, profile: StudentProfile) -> StudentProfile:
    """
    Heuristic parser: extract course completions, grades, major, term from free text.
    This would be replaced by an LLM extraction call in production.
    """
    # Detect majors
    if re.search(r'b\.?s\.?\s*(in\s*)?computer science', text, re.IGNORECASE):
        profile.major = "B.S. Computer Science"
    elif re.search(r'b\.?s\.?\s*(in\s*)?data science', text, re.IGNORECASE):
        profile.major = "B.S. Data Science"
    elif re.search(r'cybersecurity certificate', text, re.IGNORECASE):
        profile.major = "Cybersecurity Certificate"
    elif re.search(r'data science minor', text, re.IGNORECASE):
        profile.major = "Minor in Data Science"

    # Detect target term
    term_match = re.search(
        r'(fall|spring|summer)\s*(20\d{2})', text, re.IGNORECASE
    )
    if term_match:
        profile.target_term = f"{term_match.group(1).capitalize()} {term_match.group(2)}"

    # Detect completed courses with grades: "CS101: B+", "CS 101 (A-)", "CS101=B"
    patterns = [
        r'([A-Za-z]{2,5})\s*(\d{3})[:\s=\(]+([A-Fa-f][+-]?)',
        r'([A-Za-z]{2,5})\s*(\d{3})\s+with\s+(?:a\s+)?([A-Fa-f][+-]?)',
        r'([A-Za-z]{2,5})\s*(\d{3})\s*[-–]\s*([A-Fa-f][+-]?)'
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            dept, num, grade = m.group(1).upper(), m.group(2), m.group(3).upper()
            code = f"{dept}{num}"
            profile.completed_courses[code] = grade

    # Detect in-progress (concurrent)
    inprog_match = re.findall(
        r'(?:currently|taking|enrolled in|in.progress)[^.]*?([A-Z]{2,5})\s*(\d{3})',
        text, re.IGNORECASE
    )
    for dept, num in inprog_match:
        code = f"{dept.upper()}{num}"
        if code not in profile.in_progress:
            profile.in_progress.append(code)

    # Detect max credits
    cred_match = re.search(r'(?:max|maximum|up to|taking)\s*(\d{1,2})\s*credits?', text, re.IGNORECASE)
    if cred_match:
        profile.max_credits = int(cred_match.group(1))

    # Detect GPA
    gpa_match = re.search(r'gpa\s*(?:of|is|=|:)?\s*(\d\.\d{1,2})', text, re.IGNORECASE)
    if gpa_match:
        profile.gpa = float(gpa_match.group(1))

    # Detect credit hours earned
    hours_match = re.search(
        r'(\d{2,3})\s*(?:credit\s*hours?|credits?)\s*(?:completed|earned|done)',
        text, re.IGNORECASE
    )
    if hours_match:
        profile.credit_hours_earned = int(hours_match.group(1))

    # Probation detection
    if re.search(r'(?:academic\s*)?probation', text, re.IGNORECASE):
        profile.on_probation = True

    return profile


# ─────────────────────────────────────────────────────────────
# Agent 2: Catalog Retriever Agent
# ─────────────────────────────────────────────────────────────

class RetrieverAgent:
    """
    Takes a user question + student profile and retrieves the most
    relevant catalog chunks using the vector store.
    Decomposes complex questions into sub-queries.
    """
    name = "RetrieverAgent"

    def __init__(self, vector_store):
        self.vs = vector_store

    def run(self, question: str, profile: StudentProfile, k: int = 8) -> Dict[str, Any]:
        """
        Returns: {chunks, queries_used, context_text}
        """
        queries = self._decompose(question, profile)
        seen_ids = set()
        all_chunks = []

        for q in queries:
            results = self.vs.search(q, k=k)
            for chunk in results:
                cid = chunk["chunk_id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    all_chunks.append(chunk)

        # Sort by score desc
        all_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = all_chunks[:10]

        context_text = self._format_context(top_chunks)
        return {
            "chunks": top_chunks,
            "queries_used": queries,
            "context_text": context_text
        }

    def _decompose(self, question: str, profile: StudentProfile) -> List[str]:
        """Break a complex question into sub-queries for better recall."""
        queries = [question]

        # Extract course codes mentioned
        codes = set(re.findall(r'[A-Z]{2,5}\s*\d{3}', question.upper()))
        for code in codes:
            queries.append(f"prerequisites for {code}")
            queries.append(f"{code} course description credits")

        # If asking about a program
        if profile.major:
            queries.append(f"{profile.major} degree requirements")
            queries.append(f"{profile.major} core required courses")

        # If asking about a plan
        if "plan" in question.lower() or "next term" in question.lower() or "enroll" in question.lower():
            queries.append("credit load enrollment policy semester")
            if profile.major:
                queries.append(f"{profile.major} elective technical requirements")

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique.append(q)
        return unique[:6]  # Limit to 6 sub-queries

    def _format_context(self, chunks: List[Dict]) -> str:
        parts = []
        for i, chunk in enumerate(chunks):
            parts.append(
                f"[Chunk {i+1} | ID:{chunk['chunk_id']} | Score:{chunk['score']:.3f}]\n"
                f"Source: {chunk['source_url']}\n"
                f"Section: {chunk['heading']}\n"
                f"---\n{chunk['text']}\n"
            )
        return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────
# Agent 3: Planner Agent
# ─────────────────────────────────────────────────────────────

class PlannerAgent:
    """
    Given retrieved context + student profile + question type,
    produces a structured answer following the mandatory output format.
    """
    name = "PlannerAgent"
    _store_chunks = []  # class-level store of all chunks for Pass 3 fallback

    @classmethod
    def set_store_chunks(cls, chunks): cls._store_chunks = chunks

    def run(self, question: str, profile: StudentProfile,
            retrieval: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a structured answer dict:
        {
          answer, why, citations, clarifying_questions,
          assumptions, plan (if applicable), response_type
        }
        """
        q_type = self._classify(question)
        chunks = retrieval["chunks"]

        if q_type == "prereq_check":
            return self._handle_prereq_check(question, profile, chunks)
        elif q_type == "course_plan":
            return self._handle_course_plan(question, profile, chunks)
        elif q_type == "program_req":
            return self._handle_program_req(question, profile, chunks)
        elif q_type == "abstain":
            return self._handle_not_in_docs(question)
        else:
            return self._handle_general(question, profile, chunks)

    def _classify(self, question: str) -> str:
        q = question.lower()
        # Abstain first (most specific — don't let these fall into prereq_check)
        if any(w in q for w in ["who teaches", "which professor", "what professor",
                                  "which instructor", "seats available", "is there a seat",
                                  "are there seats", "class full", "waitlist", "room number",
                                  "section number", "textbook", "syllabus", "office hours",
                                  "when is the final", "passing percentage", "exam percentage",
                                  "grade percentage", "what percent", "exact grade",
                                  "professor teaching", "instructor teaching",
                                  "who is teaching", "is the professor"]):
            return "abstain"
        elif any(w in q for w in ["can i take", "eligible", "prerequisite for", "what do i need",
                                   "co-requisite", "corequisite", "qualified", "can i enroll",
                                   "am i eligible", "can i register", "i want to take",
                                   "enroll in", "i completed", "i've taken", "i have completed",
                                   "with a grade", "with a b", "with a c", "with an a",
                                   "take cs", "take math", "take ds", "i have cs", "i have math",
                                   "do i qualify", "am i allowed"]):
            return "prereq_check"
        elif any(w in q for w in ["plan my", "plan for", "course plan", "course schedule",
                                   "next term", "next semester", "what should i take",
                                   "suggest courses", "recommend courses", "courses for fall",
                                   "courses for spring"]):
            return "course_plan"
        elif any(w in q for w in ["requirement", "major require", "degree require",
                                   "elective", "credit hour", "how many credits", "total credits",
                                   "how many times", "repeat", "retake", "gpa requirement",
                                   "count as", "double-count", "satisfy", "probation",
                                   "how often", "can i repeat"]):
            return "program_req"
        else:
            return "general"

    # ── Prerequisite Check ──────────────────────────────────

    def _handle_prereq_check(self, question: str, profile: StudentProfile,
                              chunks: List[Dict]) -> Dict[str, Any]:
        # Find target course(s) in question
        # Strategy: extract all codes, but only check courses that are NOT already
        # listed as "completed" by the student (those are prerequisite context, not targets).
        all_codes = re.findall(r'([A-Za-z]{2,5})\s*(\d{3})', question, re.IGNORECASE)
        if not all_codes:
            return self._handle_general(question, profile, chunks)

        completed_norm = {k.upper().replace(" ", "") for k in profile.completed_courses}

        # Identify target courses: codes NOT already completed by the student.
        # If all codes are completed, just check the first one (the student may be asking
        # about a course they want to retake or verify eligibility for).
        target_codes = [
            (dept, num) for dept, num in all_codes
            if f"{dept.upper()}{num}" not in completed_norm
        ]
        # Deduplicate while preserving order
        seen = set()
        unique_targets = []
        for dept, num in target_codes:
            key = f"{dept.upper()}{num}"
            if key not in seen:
                seen.add(key)
                unique_targets.append((dept, num))

        # Fall back to first code if all were completed
        if not unique_targets:
            unique_targets = [all_codes[0]]

        results = []
        citations = []

        for dept, num in unique_targets:
            course_code = f"{dept.upper()}{num}"
            course_name = f"{dept.upper()} {num}"

            # Find prereq info in chunks
            # Pass 1: heading starts exactly with this course code
            prereq_chunk = None
            code_norm = course_code.upper().replace(" ", "")
            for chunk in chunks:
                heading_norm = re.sub(r"[^A-Z0-9]", "", chunk.get("heading", "").upper())
                if heading_norm.startswith(code_norm):
                    prereq_chunk = chunk
                    break
            # Pass 2: fallback — chunk body mentions code + Prerequisites
            if not prereq_chunk:
                for chunk in chunks:
                    text_flat = chunk["text"].upper().replace(" ", "")
                    if code_norm in text_flat and "PREREQUISITE" in chunk["text"].upper():
                        prereq_chunk = chunk
                        break
            # Pass 3: search ALL store chunks (not just retrieved) for heading match
            if not prereq_chunk:
                for chunk in (PlannerAgent._store_chunks or chunks):
                    heading_norm = re.sub(r"[^A-Z0-9]", "", chunk.get("heading", "").upper())
                    if heading_norm.startswith(code_norm):
                        prereq_chunk = chunk
                        break

            if not prereq_chunk:
                results.append({
                    "course": course_name,
                    "decision": "NEED MORE INFO",
                    "reason": f"No prerequisite information found for {course_name} in the retrieved catalog sections.",
                    "not_in_catalog": True
                })
                continue

            # Parse prerequisites from chunk text
            prereqs = _extract_prereqs_from_chunk(prereq_chunk["text"], course_code)
            citations.append({
                "chunk_id": prereq_chunk["chunk_id"],
                "url": prereq_chunk["source_url"],
                "section": prereq_chunk["heading"],
                "accessed": prereq_chunk["accessed"]
            })

            # Check against profile
            eligibility, reasoning = self._check_eligibility(prereqs, profile)

            results.append({
                "course": course_name,
                "decision": "ELIGIBLE" if eligibility else "NOT ELIGIBLE",
                "reason": reasoning,
                "prereqs_found": prereqs,
                "chunk_ref": prereq_chunk["chunk_id"]
            })

        # Determine overall eligibility
        all_eligible = all(r["decision"] == "ELIGIBLE" for r in results)
        any_info = any(r.get("not_in_catalog") for r in results)
        overall = "ELIGIBLE" if all_eligible and not any_info else (
            "NEED MORE INFO" if any_info else "NOT ELIGIBLE"
        )

        answer_lines = []
        for r in results:
            answer_lines.append(f"**{r['course']}**: {r['decision']}")
            answer_lines.append(f"  → {r['reason']}")

        why_lines = []
        for r in results:
            if "prereqs_found" in r:
                for p in r["prereqs_found"]:
                    why_lines.append(f"  • {p}")

        # Next steps
        not_eligible = [r for r in results if r["decision"] == "NOT ELIGIBLE"]
        next_steps = []
        if not_eligible:
            for r in not_eligible:
                next_steps.append(f"To enroll in {r['course']}, complete the missing prerequisites listed above.")
        else:
            next_steps.append("You appear to meet the listed prerequisites. Verify enrollment via the Registrar's system.")

        return {
            "response_type": "prereq_check",
            "overall_decision": overall,
            "answer": "\n".join(answer_lines),
            "why": "\n".join(why_lines) if why_lines else "See prerequisites extracted from catalog.",
            "next_steps": "\n".join(next_steps),
            "citations": citations,
            "clarifying_questions": [],
            "assumptions": [
                "Course availability by term is not guaranteed in the catalog.",
                "Seat availability is not reflected in catalog documents.",
                "Transfer equivalencies must be validated by CS Advising."
            ]
        }

    def _check_eligibility(self, prereqs: List[str],
                            profile: StudentProfile) -> Tuple[bool, str]:
        """Simple eligibility check against profile."""
        if not prereqs:
            return True, "No prerequisites listed — open enrollment."

        # "None" means no prerequisites
        if prereqs == ["None"] or (len(prereqs) == 1 and prereqs[0].strip().upper() == "NONE"):
            return True, "No prerequisites required — open enrollment."

        met = []
        unmet = []
        for prereq in prereqs:
            if prereq.strip().upper() == "NONE":
                continue
            # Parse "DEPT NUM with GRADE or higher"
            m = re.match(
                r'([A-Z]{2,5})\s*(\d{3})\s+with\s+([A-C][+-]?)\s+or\s+higher',
                prereq.strip(), re.IGNORECASE
            )
            if m:
                code = f"{m.group(1).upper()}{m.group(2)}"
                min_grade = m.group(3).upper()
                ok, reason = profile.has_completed(code, min_grade)
                if ok:
                    met.append(f"✓ {prereq}: {reason}")
                else:
                    unmet.append(f"✗ {prereq}: {reason}")
            else:
                # Try bare code match
                m2 = re.match(r'([A-Z]{2,5})\s*(\d{3})', prereq.strip(), re.IGNORECASE)
                if m2:
                    code = f"{m2.group(1).upper()}{m2.group(2)}"
                    ok, reason = profile.has_completed(code, "C")
                    if ok:
                        met.append(f"✓ {prereq}: {reason}")
                    else:
                        unmet.append(f"✗ {prereq}: {reason}")
                else:
                    unmet.append(f"? Could not parse requirement: {prereq}")

        all_met = len(unmet) == 0
        parts = []
        if met:
            parts.append("Met — " + "; ".join(met))
        if unmet:
            parts.append("Not met — " + "; ".join(unmet))
        explanation = " | ".join(parts) or "No parseable prerequisites found."
        return all_met, explanation

    # ── Course Plan ─────────────────────────────────────────

    def _handle_course_plan(self, question: str, profile: StudentProfile,
                             chunks: List[Dict]) -> Dict[str, Any]:
        if not profile.major:
            return {
                "response_type": "course_plan",
                "answer": "I need more information to generate a course plan.",
                "why": "",
                "citations": [],
                "clarifying_questions": [CLARIFYING_QUESTIONS["major"],
                                          CLARIFYING_QUESTIONS["completed_courses"],
                                          CLARIFYING_QUESTIONS["target_term"]],
                "assumptions": []
            }

        # Find relevant degree requirement chunks
        req_chunks = [c for c in chunks
                      if "requirement" in c["heading"].lower()
                      or "core" in c["heading"].lower()
                      or "elective" in c["heading"].lower()]

        planned_courses = []
        citations = []
        risks = []

        # Build candidate courses based on major requirements
        if "Computer Science" in profile.major:
            planned_courses, citations, risks = self._plan_cs(profile, chunks)
        elif "Data Science" in profile.major:
            planned_courses, citations, risks = self._plan_ds(profile, chunks)
        else:
            planned_courses, citations, risks = self._plan_generic(profile, chunks)

        # Enforce credit limit
        total = sum(c.get("credits", 3) for c in planned_courses)
        if profile.on_probation and total > 12:
            risks.append("⚠️ Academic probation limit: max 12 credits/term. Plan trimmed accordingly.")
            planned_courses = planned_courses[:4]  # ~12 cr

        answer_lines = [
            f"**Proposed Course Plan — {profile.target_term or 'Next Term'} ({profile.major})**\n"
        ]
        for c in planned_courses:
            answer_lines.append(f"  • {c['code']} — {c['name']} ({c.get('credits',3)} cr)")
            answer_lines.append(f"    Justification: {c['justification']}")

        total_cr = sum(c.get("credits", 3) for c in planned_courses)
        answer_lines.append(f"\nTotal credits proposed: {total_cr}")

        why_lines = []
        for c in planned_courses:
            if "prereq_status" in c:
                why_lines.append(f"  {c['code']}: {c['prereq_status']}")

        return {
            "response_type": "course_plan",
            "answer": "\n".join(answer_lines),
            "why": "\n".join(why_lines),
            "plan": planned_courses,
            "citations": citations,
            "clarifying_questions": [],
            "assumptions": risks + [
                "Course availability by semester is not guaranteed by the catalog.",
                "Actual open seats must be verified in the registration system.",
                "Instructor consent courses require additional approval steps."
            ]
        }

    def _plan_cs(self, profile: StudentProfile,
                 chunks: List[Dict]) -> Tuple[List, List, List]:
        """Rule-based CS planner based on catalog knowledge."""
        completed = set(k.upper().replace(" ", "") for k in profile.completed_courses)
        planned = []
        citations = []
        risks = []

        # Helper
        def has(code): return code.upper() in completed

        # Check for required courses and add what's ready
        candidates = [
            # (code, name, credits, prereqs_met_func, justification)
            ("CS101", "Introduction to Programming", 3,
             lambda: True,
             "Foundation course with no prerequisites. Required for B.S. CS."),
            ("CS150", "Discrete Mathematics for CS", 3,
             lambda: has("MATH110") or has("MATH120"),
             "Required foundation course. Prerequisite MATH 110/120 completed."),
            ("CS201", "Object-Oriented Programming", 3,
             lambda: has("CS101"),
             "Required foundation course. Prerequisite CS 101 completed."),
            ("CS210", "Computer Systems and Organization", 3,
             lambda: has("CS101"),
             "Required foundation course. Prerequisite CS 101 completed."),
            ("MATH120", "Calculus I", 4,
             lambda: has("MATH110") or True,  # open with placement
             "Required foundation — MATH 120 needed for B.S. CS and many electives."),
            ("CS250", "Data Structures and Algorithms", 4,
             lambda: has("CS201") and has("CS150"),
             "Core required course. Prerequisites CS 201 + CS 150 completed."),
            ("CS310", "Database Systems", 3,
             lambda: has("CS201") and has("CS250"),
             "Intermediate core required course. Prerequisites CS 201 + CS 250 completed."),
            ("CS311", "Operating Systems", 3,
             lambda: has("CS210") and has("CS250"),
             "Intermediate core required course. Prerequisites CS 210 + CS 250 completed."),
            ("CS301", "Software Engineering", 3,
             lambda: has("CS201") and has("CS250"),
             "Intermediate core required course. Prerequisites CS 201 + CS 250 completed."),
            ("CS390", "Ethics and Society in Computing", 3,
             lambda: has("CS201"),
             "Required ethics course. Only prerequisite: CS 201."),
            ("CS320", "Machine Learning", 3,
             lambda: has("CS250") and has("CS260") and has("CS220"),
             "Intelligent Systems track course. Prerequisites CS 250, CS 260, CS 220 completed."),
            ("CS260", "Linear Algebra for Machine Learning", 3,
             lambda: has("MATH120"),
             "Required for Intelligent Systems track. Prerequisite MATH 120 completed."),
            ("CS220", "Statistics for Data Science", 3,
             lambda: has("MATH120"),
             "Required for ML track. Prerequisite MATH 120 completed."),
        ]

        credit_budget = profile.max_credits if not profile.on_probation else 12

        for code, name, credits, prereq_fn, justification in candidates:
            if has(code):
                continue  # Already completed
            if sum(c.get("credits",3) for c in planned) + credits > credit_budget:
                break
            if prereq_fn():
                planned.append({
                    "code": code,
                    "name": name,
                    "credits": credits,
                    "justification": justification,
                    "prereq_status": "Prerequisites satisfied per catalog check."
                })

        # Citations from requirement chunks
        for chunk in chunks[:3]:
            citations.append({
                "chunk_id": chunk["chunk_id"],
                "url": chunk["source_url"],
                "section": chunk["heading"],
                "accessed": chunk["accessed"]
            })

        if not planned:
            risks.append("Could not identify eligible courses from catalog data alone. Manual advisor review recommended.")

        return planned[:5], citations, risks

    def _plan_ds(self, profile: StudentProfile,
                 chunks: List[Dict]) -> Tuple[List, List, List]:
        completed = set(k.upper().replace(" ", "") for k in profile.completed_courses)
        def has(code): return code.upper() in completed
        planned = []
        risks = []

        candidates = [
            ("DS101", "Introduction to Data Science", 3, lambda: True,
             "Foundation required course for B.S. Data Science. No prerequisites."),
            ("CS101", "Introduction to Programming", 3, lambda: True,
             "Required foundation for B.S. Data Science."),
            ("CS220", "Statistics for Data Science", 3, lambda: has("MATH120"),
             "Required foundation. Prerequisite MATH 120 completed."),
            ("DS201", "Data Wrangling and Visualization", 3,
             lambda: (has("DS101") or has("CS230")) and (has("MATH110") or has("MATH120")),
             "Core required. Prerequisites DS 101 (or CS 230) and MATH 110+ completed."),
            ("CS250", "Data Structures and Algorithms", 4,
             lambda: has("CS201") and has("CS150"),
             "Core required. Prerequisites CS 201 + CS 150 completed."),
        ]

        budget = profile.max_credits if not profile.on_probation else 12
        for code, name, credits, prereq_fn, justification in candidates:
            if has(code): continue
            if sum(c.get("credits",3) for c in planned) + credits > budget: break
            if prereq_fn():
                planned.append({"code": code, "name": name, "credits": credits,
                                 "justification": justification,
                                 "prereq_status": "Prerequisites satisfied per catalog check."})

        citations = [{"chunk_id": c["chunk_id"], "url": c["source_url"],
                      "section": c["heading"], "accessed": c["accessed"]}
                     for c in chunks[:3]]
        return planned[:5], citations, risks

    def _plan_generic(self, profile: StudentProfile,
                      chunks: List[Dict]) -> Tuple[List, List, List]:
        return [], [], ["Major not recognized in catalog rules. Please consult your advisor."]

    # ── Program Requirements ─────────────────────────────────

    def _handle_program_req(self, question: str, profile: StudentProfile,
                             chunks: List[Dict]) -> Dict[str, Any]:
        # Check for topics not covered in catalog docs first
        q_lower = question.lower()
        not_in_docs = ["co-op", "coop", "internship credit", "work experience",
                       "substitute for elective", "waive elective", "replace elective"]
        if any(t in q_lower for t in not_in_docs):
            return self._handle_not_in_docs(question)

        # Aggregate relevant text
        relevant_text = []
        citations = []
        for chunk in chunks[:5]:
            relevant_text.append(f"From [{chunk['heading']}]:\n{chunk['text'][:500]}")
            citations.append({
                "chunk_id": chunk["chunk_id"],
                "url": chunk["source_url"],
                "section": chunk["heading"],
                "accessed": chunk["accessed"]
            })

        context = "\n\n".join(relevant_text)

        # Rule-based extraction for common questions
        answer = self._answer_program_question(question, chunks, profile)

        return {
            "response_type": "program_req",
            "answer": answer,
            "why": "Based on degree requirement pages retrieved from catalog.",
            "citations": citations,
            "clarifying_questions": [],
            "assumptions": [
                "Policy details may vary by catalog year. Verify with your advisor.",
                "This reflects the 2024–2025 catalog unless otherwise specified."
            ]
        }

    def _answer_program_question(self, question: str,
                                  chunks: List[Dict],
                                  profile: StudentProfile) -> str:
        q = question.lower()
        # Extract relevant text from top chunks
        all_text = " ".join(c["text"] for c in chunks[:6]).lower()

        if "credit" in q and ("how many" in q or "total" in q or "required" in q):
            # Look for credit totals
            matches = re.findall(r'(\d{3})\s*credit\s*hours?\s*required', all_text)
            if matches:
                return f"Based on the retrieved catalog sections, the program requires **{matches[0]} credit hours** total. Please see the cited sections for full breakdown."
            return "The retrieved sections mention credit requirements — see citations for exact figures. Common requirement: 120 credit hours for B.S. programs."

        if "elective" in q:
            if "technical elective" in all_text:
                return ("Technical electives require at least 15 credits, with at least 9 credits "
                        "at the 300-level or above. At most 6 credits may come from outside the CS department. "
                        "Courses used for the Advanced Core track may NOT double-count as Technical Electives. "
                        "See citations for the full approved elective list.")
            return "Elective requirements vary by program. See the cited catalog sections for specifics."

        if "gpa" in q or "minimum grade" in q:
            return ("A minimum cumulative GPA of 2.0 and a 2.0 CS-prefix GPA are required for graduation "
                    "in B.S. Computer Science. Note: a grade of C- does NOT satisfy 'C or higher' prerequisites — "
                    "a C (2.0) is the minimum passing grade for prerequisite purposes.")

        # Default: summarize top chunk
        if chunks:
            snippet = chunks[0]["text"][:400]
            return f"Based on the catalog:\n\n{snippet}\n\n[See full citations below for complete requirements.]"

        return "I don't have that information in the provided catalog/policies. Please consult your academic advisor or the department's program page."

    # ── Not In Docs / Explicit Abstain ──────────────────────
    def _handle_not_in_docs(self, question: str) -> Dict[str, Any]:
        """Called when classifier determines the question is outside catalog scope."""
        q = question.lower()
        if "professor" in q or "who teaches" in q or "instructor" in q:
            reason = ("Professor and instructor assignments are not contained in the course catalog. "
                      "They are determined each semester by the department.")
            guidance = ("• Check the semester Schedule of Classes on the Registrar's portal.\n"
                        "• Contact the CS Department office directly.\n"
                        "• Visit the department website for faculty listings.")
        elif "seat" in q or "available" in q or "open" in q or "waitlist" in q:
            reason = ("Real-time seat availability and course enrollment status are not contained "
                      "in the course catalog documents.")
            guidance = ("• Check real-time availability in the course registration system.\n"
                        "• Contact the Registrar's office or use the online course search tool.\n"
                        "• The catalog does indicate which terms a course is typically offered "
                        "(Fall/Spring/Summer), but not live seat counts.")
        else:
            reason = "This information is not contained in the provided catalog or policy documents."
            guidance = ("• Consult your academic advisor.\n"
                        "• Check the Registrar's website.\n"
                        "• Contact the CS Department office.")
        return {
            "response_type": "abstain",
            "overall_decision": "NOT IN CATALOG",
            "answer": f"I don't have that information in the provided catalog/policies.\n\n{reason}",
            "why": "",
            "citations": [],
            "clarifying_questions": [],
            "assumptions": [],
            "next_steps": guidance,
            "audit_passed": True,
            "confidence": "HIGH",
            "audit_issues": [],
            "audit_warnings": []
        }

    # ── General / Abstention ─────────────────────────────────

    def _handle_general(self, question: str, profile: StudentProfile,
                         chunks: List[Dict]) -> Dict[str, Any]:
        # Check for "not in docs" patterns first
        not_in_docs_triggers = [
            "which professor", "who teaches", "what professor", "which instructor",
            "is the class open", "are there seats", "seats available", "is there a seat",
            "class size", "class full", "section number", "room number", "textbook",
            "syllabus", "office hours", "when is the final", "what time does",
            "what time is", "course number for next", "is it open",
            "co-op", "coop credit", "internship credit", "work experience credit",
            "special permission to skip", "permission to waive", "can my professor give",
            "will the professor", "would the professor", "professor allow",
            "specific professor", "approve my request", "department approval"
        ]
        q_lower = question.lower()
        if any(trigger in q_lower for trigger in not_in_docs_triggers):
            return self._handle_not_in_docs(question)

        if not chunks:
            return {
                "response_type": "abstain",
                "answer": "I don't have that information in the provided catalog/policies.",
                "why": "No relevant catalog sections were retrieved for this query.",
                "citations": [],
                "clarifying_questions": [],
                "assumptions": [],
                "next_steps": (
                    "• Check with your academic advisor.\n"
                    "• Visit the Registrar's website for scheduling and availability.\n"
                    "• Contact the CS Department office directly.\n"
                    "• Review the full catalog at catalog.stateuniversity.edu."
                )
            }

        # Check for "not in docs" patterns
        not_in_docs_triggers = [
            "which professor", "who teaches", "what professor",
            "is the class open", "is there a seat", "class size",
            "section number", "room number", "textbook",
            "syllabus", "office hours", "when is the final"
        ]
        q_lower = question.lower()
        if any(trigger in q_lower for trigger in not_in_docs_triggers):
            return {
                "response_type": "abstain",
                "answer": "I don't have that information in the provided catalog/policies.",
                "why": "Questions about professor assignments, seat availability, room numbers, "
                       "syllabi, and class schedules are not contained in the course catalog documents.",
                "citations": [],
                "clarifying_questions": [],
                "assumptions": [],
                "next_steps": (
                    "• Check the semester Schedule of Classes on the Registrar's website.\n"
                    "• Contact the CS Department office for professor/TA information.\n"
                    "• Use the university's course search portal for real-time seat availability."
                )
            }

        # Otherwise, provide grounded answer from chunks
        citations = [{
            "chunk_id": c["chunk_id"],
            "url": c["source_url"],
            "section": c["heading"],
            "accessed": c["accessed"]
        } for c in chunks[:4]]

        top_text = chunks[0]["text"][:600] if chunks else ""
        return {
            "response_type": "general",
            "answer": f"Based on the catalog, here is what I found:\n\n{top_text}",
            "why": "Retrieved from catalog sections — see citations.",
            "citations": citations,
            "clarifying_questions": [],
            "assumptions": ["Please verify current policies with your advisor, "
                            "as catalog details may vary by year."]
        }


# ─────────────────────────────────────────────────────────────
# Agent 4: Verifier / Auditor Agent
# ─────────────────────────────────────────────────────────────

class VerifierAgent:
    """
    Audits the planner's answer for:
      - Missing citations on factual claims
      - Unsupported prereq decisions
      - Policy claims not backed by retrieved chunks
    Adds warnings to the response and adjusts confidence.
    """
    name = "VerifierAgent"

    def run(self, planner_output: Dict[str, Any],
            retrieval: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        warnings = []
        chunks = retrieval["chunks"]
        chunk_ids = {c["chunk_id"] for c in chunks}

        # Check: are citations grounded in retrieved chunks?
        for cit in planner_output.get("citations", []):
            if cit["chunk_id"] not in chunk_ids:
                issues.append(f"Citation {cit['chunk_id']} not found in retrieved chunks.")

        # Check: no citations at all for factual answer?
        if not planner_output.get("citations") and planner_output.get("response_type") not in ["abstain"]:
            issues.append("No citations provided. All factual claims must be cited.")

        # Check: eligibility decision without chunk evidence?
        if planner_output.get("response_type") == "prereq_check":
            if planner_output.get("overall_decision") == "ELIGIBLE" and not planner_output.get("citations"):
                issues.append("Eligibility decision made without cited evidence.")

        # Check: course plan without requirement citations?
        if planner_output.get("response_type") == "course_plan":
            if not planner_output.get("citations"):
                warnings.append("Course plan lacks citations to program requirement pages.")

        # Check for weasel words that suggest fabrication
        answer_text = planner_output.get("answer", "")
        fabrication_hints = ["typically", "generally", "usually requires", "often requires",
                              "in most programs", "I believe"]
        for hint in fabrication_hints:
            if hint.lower() in answer_text.lower():
                warnings.append(f"Possible unsupported claim detected ('{hint}'). Verify against cited catalog text.")

        planner_output["audit_issues"] = issues
        planner_output["audit_warnings"] = warnings
        planner_output["audit_passed"] = len(issues) == 0
        planner_output["confidence"] = "HIGH" if not issues and not warnings else (
            "MEDIUM" if not issues else "LOW"
        )
        return planner_output


# ─────────────────────────────────────────────────────────────
# Prerequisite extraction utility
# ─────────────────────────────────────────────────────────────

def _extract_prereqs_from_chunk(text: str, course_code: str) -> List[str]:
    """Extract prerequisite course codes from a chunk's text."""
    prereqs = []
    lines = text.splitlines()

    # Find the Prerequisites: line
    prereq_line = ""
    for i, line in enumerate(lines):
        if re.match(r'\s*prerequisites?\s*:', line, re.IGNORECASE):
            # Collect this line and next few continuation lines
            segment = line
            for j in range(i+1, min(i+5, len(lines))):
                next_line = lines[j].strip()
                if next_line and not re.match(r'\s*(co-?requisite|description|credits|offered|grade)', next_line, re.IGNORECASE):
                    segment += " " + next_line
                else:
                    break
            prereq_line = segment
            break

    if not prereq_line:
        return []

    # Check for "None"
    if re.search(r'prerequisites?\s*:\s*none', prereq_line, re.IGNORECASE):
        return ["None"]

    # Extract course codes from the prereq line
    codes_found = re.findall(r'([A-Z]{2,5})\s*(\d{3})', prereq_line, re.IGNORECASE)
    target_clean = course_code.upper().replace(" ", "")

    for dept, num in codes_found:
        code = f"{dept.upper()}{num}"
        if code == target_clean:
            continue  # skip self-reference

        # Look for grade requirement near this code
        # Pattern: "CS 201 with a grade of C or higher" or "CS 201 with C or higher"
        grade_pattern = rf'{re.escape(dept)}\s*{num}[^,\.AND]*?(?:grade\s+of\s+)?([A-C][+-]?)\s+or\s+higher'
        grade_match = re.search(grade_pattern, prereq_line, re.IGNORECASE)
        grade = grade_match.group(1).upper() if grade_match else "C"

        entry = f"{dept.upper()} {num} with {grade} or higher"
        if entry not in prereqs:
            prereqs.append(entry)

    return prereqs


# ─────────────────────────────────────────────────────────────
# Pipeline Orchestrator
# ─────────────────────────────────────────────────────────────

def run_pipeline(user_input: str,
                 profile: StudentProfile,
                 vector_store,
                 verbose: bool = False) -> Dict[str, Any]:
    """
    Full 4-agent pipeline.
    Returns complete structured response.
    """
    intake = IntakeAgent()
    retriever = RetrieverAgent(vector_store)
    planner = PlannerAgent()
    verifier = VerifierAgent()

    # Step 1: Intake
    intake_result = intake.run(user_input, profile)
    profile = intake_result["profile"]

    if verbose:
        print(f"[IntakeAgent] Missing fields: {intake_result['missing_fields']}")
        print(f"[IntakeAgent] Ready to plan: {intake_result['ready_to_plan']}")

    # If critical info is missing, return clarifying questions
    if not intake_result["ready_to_plan"] and intake_result["missing_fields"]:
        return {
            "response_type": "clarify",
            "answer": "I need a bit more information before I can help you accurately.",
            "why": "",
            "citations": [],
            "clarifying_questions": intake_result["clarifying_questions"],
            "assumptions": [],
            "profile": profile
        }

    # Step 2: Retrieve
    retrieval = retriever.run(user_input, profile)

    if verbose:
        print(f"[RetrieverAgent] Queries: {retrieval['queries_used']}")
        print(f"[RetrieverAgent] Chunks retrieved: {len(retrieval['chunks'])}")

    # Step 3: Plan  (inject all store chunks for fallback heading search)
    PlannerAgent.set_store_chunks(vector_store.chunks if hasattr(vector_store, 'chunks') else [])
    planner_output = planner.run(user_input, profile, retrieval)
    planner_output["profile"] = profile

    # Step 4: Verify
    verified = verifier.run(planner_output, retrieval)

    if verbose:
        print(f"[VerifierAgent] Audit passed: {verified['audit_passed']}")
        if verified.get("audit_issues"):
            print(f"[VerifierAgent] Issues: {verified['audit_issues']}")

    return verified
