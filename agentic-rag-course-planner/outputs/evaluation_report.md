# RAG Prerequisite Assistant — Evaluation Report

## Aggregate Metrics

| Metric | Score |
|--------|-------|
| **Citation Coverage Rate** | 80% |
| **Eligibility Decision Accuracy (prereq checks)** | 90% |
| **Prerequisite Chain Accuracy** | 80% |
| **Program Requirement Accuracy** | 100% |
| **Abstention Accuracy (not-in-docs)** | 100% |
| **Audit Pass Rate** | 96% |
| **Overall Score** | 69% |

## Per-Query Results

| ID | Category | Score | Cited | Decision✓ | Abstain✓ | Notes |
|----|----------|-------|-------|-----------|----------|-------|
| A01 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A02 | prereq_check | 7/10 | ✓ | ✓ | ✓ | — |
| A03 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A04 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A05 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A06 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A07 | prereq_check | 7/10 | ✓ | ✓ | ✓ | — |
| A08 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A09 | prereq_check | 8/10 | ✓ | ✓ | ✓ | — |
| A10 | prereq_check | 1/10 | ✓ | ✗ | ✓ | FAIL: Expected NOT ELIGIBLE, got ELIGIBLE |
| B01 | prereq_chain | 6/10 | ✓ | ✓ | ✓ | — |
| B02 | prereq_chain | 3/10 | ✓ | ✗ | ✓ | FAIL: Expected NEED MORE INFO, got GENERAL |
| B03 | prereq_chain | 5/10 | ✓ | ✓ | ✓ | — |
| B04 | prereq_chain | 8/10 | ✓ | ✓ | ✓ | — |
| B05 | prereq_chain | 6/10 | ✓ | ✓ | ✓ | — |
| C01 | program_req | 7/10 | ✓ | ✓ | ✓ | No specific decision to evaluate; checking for grounded answ |
| C02 | program_req | 7/10 | ✓ | ✓ | ✓ | No specific decision to evaluate; checking for grounded answ |
| C03 | program_req | 7/10 | ✓ | ✓ | ✓ | No specific decision to evaluate; checking for grounded answ |
| C04 | program_req | 7/10 | ✓ | ✓ | ✓ | No specific decision to evaluate; checking for grounded answ |
| C05 | program_req | 7/10 | ✓ | ✓ | ✓ | No specific decision to evaluate; checking for grounded answ |
| D01 | not_in_docs | 8/10 | ✗ | ✓ | ✓ | PARTIAL: Correct abstention but decision label unclear. |
| D02 | not_in_docs | 8/10 | ✗ | ✓ | ✓ | PARTIAL: Correct abstention but decision label unclear. |
| D03 | not_in_docs | 8/10 | ✗ | ✓ | ✓ | PARTIAL: Correct abstention but decision label unclear. |
| D04 | not_in_docs | 6/10 | ✗ | ✓ | ✓ | PARTIAL: Correct abstention but decision label unclear. |
| D05 | not_in_docs | 8/10 | ✗ | ✓ | ✓ | PARTIAL: Correct abstention but decision label unclear. |

## Rubric


Each query is scored out of 10 points:
- **Citation Score (0–3)**: Does the response cite catalog sources? Do citations match expected sections?
- **Decision Correctness (0–4)**: Does ELIGIBLE/NOT ELIGIBLE/ABSTAIN match the ground truth?
- **Abstention Accuracy (0–2)**: For "not in docs" queries, does the system correctly abstain rather than guess?
- **Audit Pass (0–1)**: Did the internal VerifierAgent flag no major issues?

Grades: ≥80% = Excellent, 70–79% = Good, 60–69% = Needs Improvement, <60% = Poor.


---
## Transcript 1: Correct Eligibility Decision with Citations

**Query (A01):** Can I take CS 201 if I've completed CS 101 with a B+?

**Profile:** {
  "major": "B.S. Computer Science",
  "completed_courses": {
    "CS101": "B+"
  },
  "target_term": "Spring 2025"
}

**Response:**
```
## 🔍 Decision: **ELIGIBLE**

*Confidence: 🟢 HIGH*

---
## Answer / Plan

**CS 201**: ELIGIBLE
  → Met — ✓ CS 101 with C or higher: Completed CS101 with B+

---
## Why (Requirements/Prerequisites Satisfied)

  • CS 101 with C or higher

**Next Steps:**
You appear to meet the listed prerequisites. Verify enrollment via the Registrar's system.

---
## Citations

[1] **CS 201 — Object-Oriented Programming**  
    URL: https://catalog.stateuniversity.edu/courses/cs/100-200  
    Accessed: 2025-01-15  
    Chunk ID: `48f942aeae`

---
## Assumptions / Not in Catalog

• Course availability by term is not guaranteed in the catalog.
• Seat availability is not reflected in catalog documents.
• Transfer equivalencies must be validated by CS Advising.
```

**Rubric:** CS 201 requires CS 101 with C or higher. B+ satisfies this. Must cite CS 201 section.

**Evaluation:** Score 8/10 | Decision: ✓

---
## Transcript 2: Course Plan Output with Justification + Citations

**Query:** Plan my courses for Fall 2025. I'm in B.S. Computer Science.

**Profile:** CS101:A, CS150:B+, MATH120:A-, CS201:B

**Response:**
```
*Confidence: 🟢 HIGH*

---
## Answer / Plan

**Proposed Course Plan — Fall 2025 (B.S. Computer Science)**

  • CS210 — Computer Systems and Organization (3 cr)
    Justification: Required foundation course. Prerequisite CS 101 completed.
  • CS250 — Data Structures and Algorithms (4 cr)
    Justification: Core required course. Prerequisites CS 201 + CS 150 completed.
  • CS390 — Ethics and Society in Computing (3 cr)
    Justification: Required ethics course. Only prerequisite: CS 201.
  • CS260 — Linear Algebra for Machine Learning (3 cr)
    Justification: Required for Intelligent Systems track. Prerequisite MATH 120 completed.
  • CS220 — Statistics for Data Science (3 cr)
    Justification: Required for ML track. Prerequisite MATH 120 completed.

Total credits proposed: 16

---
## Why (Requirements/Prerequisites Satisfied)

  CS210: Prerequisites satisfied per catalog check.
  CS250: Prerequisites satisfied per catalog check.
  CS390: Prerequisites satisfied per catalog check.
  CS260: Prerequisites satisfied per catalog check.
  CS220: Prerequisites satisfied per catalog check.

---
## Citations

[1] **Credit Load and Overload Policy**  
    URL: https://catalog.stateuniversity.edu/policies/academic  
    Accessed: 2025-01-15  
    Chunk ID: `42b4aa19f0`
[2] **B.S. in Data Science — Overview**  
    URL: https://catalog.stateuniversity.edu/programs/bs-data-science  
    Accessed: 2025-01-15  
    Chunk ID: `3b6e2567ad`
[3] **CS 150 — Discrete Mathematics for Computer Science**  
    URL: https://catalog.stateuniversity.edu/courses/cs/100-200  
    Accessed: 2025-01-15  
    Chunk ID: `07fc8a2f60`

---
## Assumptions / Not in Catalog

• Course availability by semester is not guaranteed by the catalog.
• Actual open seats must be verified in the registration system.
• Instructor consent courses require additional approval steps.
```

---
## Transcript 3: Correct Abstention + Guidance

**Query (D01):** Is CS 310 offered this spring? Are there seats available?

**Response:**
```
## 🔍 Decision: **NOT IN CATALOG**

*Confidence: 🟢 HIGH*

---
## Answer / Plan

I don't have that information in the provided catalog/policies.

Real-time seat availability and course enrollment status are not contained in the course catalog documents.

**Next Steps:**
• Check real-time availability in the course registration system.
• Contact the Registrar's office or use the online course search tool.
• The catalog does indicate which terms a course is typically offered (Fall/Spring/Summer), but not live seat counts.

---
## Citations

*No catalog citations available for this response.*

---
## Assumptions / Not in Catalog

• None noted.
```

**Rubric:** The catalog states CS 310 is offered Fall/Spring, but real-time seat availability is NOT in the catalog. Must abstain on seat availability and direct to Registrar's Schedule of Classes.

**Evaluation:** Correct abstention | Score 8/10