"""
formatter.py — Renders the agent pipeline output in the mandatory format:

  Answer / Plan:
  Why (requirements/prereqs satisfied):
  Citations:
  Clarifying questions (if needed):
  Assumptions / Not in catalog:
"""

from typing import Dict, Any, List


def format_response(result: Dict[str, Any]) -> str:
    """Convert pipeline output dict to the mandatory markdown output format."""
    lines = []

    # ── Header ──────────────────────────────────────────────
    rtype = result.get("response_type", "general")
    decision = result.get("overall_decision", "")
    if decision:
        lines.append(f"## 🔍 Decision: **{decision}**\n")

    confidence = result.get("confidence", "")
    if confidence:
        icon = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(confidence, "⚪")
        lines.append(f"*Confidence: {icon} {confidence}*\n")

    # ── Answer / Plan ────────────────────────────────────────
    lines.append("---")
    lines.append("## Answer / Plan\n")
    answer = result.get("answer", "No answer generated.")
    lines.append(answer)

    # ── Why ──────────────────────────────────────────────────
    why = result.get("why", "")
    if why:
        lines.append("\n---")
        lines.append("## Why (Requirements/Prerequisites Satisfied)\n")
        lines.append(why)

    # Next steps (prereq checks)
    next_steps = result.get("next_steps", "")
    if next_steps:
        lines.append("\n**Next Steps:**")
        lines.append(next_steps)

    # ── Citations ─────────────────────────────────────────────
    lines.append("\n---")
    lines.append("## Citations\n")
    citations = result.get("citations", [])
    if citations:
        seen = set()
        idx = 1
        for cit in citations:
            key = (cit["url"], cit["section"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"[{idx}] **{cit['section']}**  \n"
                f"    URL: {cit['url']}  \n"
                f"    Accessed: {cit.get('accessed', 'N/A')}  \n"
                f"    Chunk ID: `{cit['chunk_id']}`"
            )
            idx += 1
    else:
        lines.append("*No catalog citations available for this response.*")

    # ── Clarifying Questions ──────────────────────────────────
    clarifying = result.get("clarifying_questions", [])
    if clarifying:
        lines.append("\n---")
        lines.append("## Clarifying Questions\n")
        lines.append("To give you a more accurate answer, please provide:\n")
        for i, q in enumerate(clarifying, 1):
            lines.append(f"{i}. {q}")

    # ── Assumptions / Not in Catalog ─────────────────────────
    assumptions = result.get("assumptions", [])
    lines.append("\n---")
    lines.append("## Assumptions / Not in Catalog\n")
    if assumptions:
        for a in assumptions:
            lines.append(f"• {a}")
    else:
        lines.append("• None noted.")

    # ── Audit Warnings ───────────────────────────────────────
    issues = result.get("audit_issues", [])
    warnings = result.get("audit_warnings", [])
    if issues or warnings:
        lines.append("\n---")
        lines.append("## ⚠️ Audit Notes (Internal)\n")
        for issue in issues:
            lines.append(f"🔴 **Issue:** {issue}")
        for w in warnings:
            lines.append(f"🟡 **Warning:** {w}")

    return "\n".join(lines)


def format_short_response(result: Dict[str, Any]) -> str:
    """One-line summary for evaluation output."""
    decision = result.get("overall_decision", result.get("response_type", "N/A"))
    ncitations = len(result.get("citations", []))
    audit = "✓" if result.get("audit_passed", False) else "✗"
    return f"[{decision}] Citations:{ncitations} Audit:{audit} Confidence:{result.get('confidence','?')}"
