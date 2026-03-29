"""
demo.py — Gradio web demo for the Prerequisite & Course Planning Assistant.

Run: python demo.py
Opens at http://localhost:7860
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vector_store import load_store, build_store
from ingestion import ingest_catalog
from agents import StudentProfile, run_pipeline
from formatter import format_response

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    print("gradio not installed. Run: pip install gradio")


# ── Load or build index ─────────────────────────────────────
INDEX_PATH = Path(__file__).parent / "outputs" / "vector_index.json"

def get_store():
    if INDEX_PATH.exists():
        return load_store(INDEX_PATH)
    chunks = ingest_catalog()
    return build_store(chunks, INDEX_PATH)


store = get_store()


# ── Core query function ─────────────────────────────────────
def answer_query(
    question: str,
    major: str,
    completed_courses_raw: str,
    target_term: str,
    credit_hours: int,
    on_probation: bool,
    max_credits: int
) -> str:
    """Parse inputs, run pipeline, return formatted response."""
    if not question.strip():
        return "Please enter a question."

    profile = StudentProfile()
    profile.major = major if major else None
    profile.target_term = target_term if target_term else None
    profile.credit_hours_earned = credit_hours
    profile.on_probation = on_probation
    profile.max_credits = max_credits

    # Parse completed courses: "CS101:A, MATH120:B+" or "CS101 A, MATH120 B+"
    if completed_courses_raw.strip():
        import re
        for item in re.split(r'[,;\n]+', completed_courses_raw):
            item = item.strip()
            m = re.match(r'([A-Za-z]{2,5})\s*(\d{3})\s*[:= ]+\s*([A-Fa-f][+-]?)', item, re.IGNORECASE)
            if m:
                code = f"{m.group(1).upper()}{m.group(2)}"
                profile.completed_courses[code] = m.group(3).upper()

    result = run_pipeline(question, profile, store, verbose=False)
    return format_response(result)


# ── Example queries ─────────────────────────────────────────
EXAMPLES = [
    ["Can I take CS 310 if I've completed CS 201 with a B and CS 250 with an A?",
     "B.S. Computer Science", "CS101:A, CS150:B, CS201:B, CS250:A", "Fall 2025", 60, False, 18],
    ["Can I take CS 250 if I have CS 201 with a C- and CS 150 with a B?",
     "B.S. Computer Science", "CS101:A, CS150:B, CS201:C-", "Spring 2025", 45, False, 18],
    ["Plan my courses for Fall 2025. I want to stay on track for B.S. Computer Science.",
     "B.S. Computer Science", "CS101:A, CS150:B+, CS201:B, MATH120:A", "Fall 2025", 45, False, 18],
    ["How many technical elective credits do I need for the B.S. in Computer Science?",
     "B.S. Computer Science", "", "Fall 2025", 0, False, 18],
    ["Who is the professor teaching CS 320 next semester?",
     "B.S. Computer Science", "", "Spring 2025", 0, False, 18],
    ["I'm on academic probation. Can I take 15 credits next term?",
     "B.S. Computer Science", "", "Fall 2025", 30, True, 15],
    ["What is the full prerequisite chain for CS 411 Distributed Systems?",
     "B.S. Computer Science", "", "Fall 2026", 0, False, 18],
    ["Can I take CS 320 Machine Learning? I have CS 250 B, CS 260 C, CS 220 D+.",
     "B.S. Computer Science", "CS250:B, CS260:C, CS220:D+", "Spring 2025", 75, False, 18],
]


# ── Gradio UI ────────────────────────────────────────────────
def build_demo():
    with gr.Blocks(
        title="🎓 Course Planning Assistant",
        theme=gr.themes.Soft(),
        css="""
        .output-box { font-family: monospace; font-size: 13px; }
        .header { text-align: center; padding: 10px; }
        """
    ) as demo:
        gr.Markdown("""
        # 🎓 Prerequisite & Course Planning Assistant
        **State University Academic Catalog RAG System**
        
        Ask about course prerequisites, degree requirements, and course planning.
        Every answer is grounded in the catalog with verifiable citations.
        
        > ⚠️ This assistant can only answer questions based on the provided catalog documents.
        > For real-time enrollment, seat availability, or professor info — contact the Registrar.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Your Profile")
                major = gr.Dropdown(
                    choices=[
                        "B.S. Computer Science",
                        "B.S. Data Science",
                        "Minor in Data Science",
                        "Cybersecurity Certificate",
                        ""
                    ],
                    value="B.S. Computer Science",
                    label="Major / Program"
                )
                completed_courses = gr.Textbox(
                    label="Completed Courses (format: CS101:B+, MATH120:A)",
                    placeholder="CS101:A, CS150:B+, CS201:B, MATH120:A-",
                    lines=3
                )
                target_term = gr.Dropdown(
                    choices=["Fall 2025", "Spring 2026", "Fall 2026", "Spring 2025", ""],
                    value="Fall 2025",
                    label="Target Term"
                )
                with gr.Row():
                    credit_hours = gr.Number(label="Credits Earned", value=0, precision=0)
                    max_credits = gr.Slider(1, 21, value=18, step=1, label="Max Credits/Term")
                on_probation = gr.Checkbox(label="On Academic Probation", value=False)

            with gr.Column(scale=2):
                gr.Markdown("### 💬 Ask a Question")
                question = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g. Can I take CS 310 if I have CS 201 B and CS 250 A?",
                    lines=3
                )
                submit_btn = gr.Button("🔍 Get Answer", variant="primary", size="lg")
                gr.Markdown("---")
                output = gr.Markdown(label="Answer", elem_classes=["output-box"])

        gr.Markdown("### 📚 Example Queries")
        gr.Examples(
            examples=EXAMPLES,
            inputs=[question, major, completed_courses, target_term,
                    credit_hours, on_probation, max_credits],
            outputs=output,
            fn=answer_query,
            cache_examples=False,
            label="Click an example to try it"
        )

        submit_btn.click(
            fn=answer_query,
            inputs=[question, major, completed_courses, target_term,
                    credit_hours, on_probation, max_credits],
            outputs=output
        )

        gr.Markdown("""
        ---
        **Sources:** State University Academic Catalog | Accessed: 2025-01-15 | 
        [catalog.stateuniversity.edu](https://catalog.stateuniversity.edu)
        """)

    return demo


if __name__ == "__main__":
    if not HAS_GRADIO:
        print("Install gradio first: pip install gradio")
        sys.exit(1)

    demo = build_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
