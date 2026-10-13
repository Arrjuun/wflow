"""Create and approve two example workflows: 'M&S Certification' and a branching 'Change Request'.

    python -m app.seed_example
"""
from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import User, Workflow, now
from .routers.workflows import apply_graph
from .schemas import WorkflowIn
from .seed import ensure_admin


def text(key, label, half=False, ph="", required=False):
    return {"key": key, "type": "text", "label": label, "required": required,
            "config": {"width": "half" if half else "full", "placeholder": ph}}


def area(key, label, ph="", required=False):
    return {"key": key, "type": "textarea", "label": label, "required": required, "config": {"placeholder": ph}}


def drop(key, label, options, half=False, required=False):
    return {"key": key, "type": "dropdown", "label": label, "required": required,
            "config": {"options": options, "width": "half" if half else "full"}}


def head(key, label, body=""):
    return {"key": key, "type": "heading", "label": label, "config": {"text": body}}


def link(key, label):
    return {"key": key, "type": "url", "label": label, "config": {"placeholder": "https://docs.google.com/spreadsheets/..."}}


def upload(key, label):
    return {"key": key, "type": "file", "label": label, "config": {}}


M_S = {
    "title": "M&S Certification",
    "description": "Model and simulation credibility process with a gate review after each phase.",
    "phases": [
        {"key": "1", "name": "Phase 1: Scope", "is_start": True, "steps": [
            {"name": "Step 1: M&S Purpose", "fields": [
                area("question", "Question of Interest", "Describe the specific question or concern the application model will address...", True),
                drop("regulation", "Applicable Regulations", ["CS/FAR 25.305 (Strength and Deformation)", "CS/FAR 25.307 (Static Strength)", "CS/FAR 25.571 (Damage Tolerance)"], required=True),
                drop("structure", "Structure", ["Wing Leading Edge", "Wing Root", "Fuselage Panel", "Landing Gear Attachment"], required=True),
                drop("loads", "Load Conditions", ["Limit Static", "Ultimate Static", "Fatigue"], required=True),
                drop("cou", "Context of Use (CoU)", ["Sole means of compliance", "Primary means with test support", "Supporting evidence"], half=True, required=True),
                area("limitation", "Limitation of Application"),
                area("system", "System (Internal vs External to model)"),
                drop("behavior", "System Behavior", ["Linear elastic", "Non-linear deformations", "Contact / friction", "Failure / damage"], half=True),
                text("state_initial", "System State (Initial)", half=True, ph="Initial State"),
                text("state_final", "System State (Final)", half=True, ph="Final State"),
                area("qoi", "Quantities of Interest (QoI)"),
            ]},
            {"name": "Step 2: Criticality Assessment", "fields": [
                area("criticality_desc", "Criticality Assessment Description", "Evaluation of the role and importance of the application model..."),
                head("matrix", "M&S Criticality Level Matrix"),
                drop("ms_influence", "M&S Influence", ["L1 (Sole means)", "L2 (Primary)", "L3 (Supporting)"], half=True, required=True),
                drop("design_influence", "Design Influence", ["LA (Catastrophic/Airworthiness)", "LB (Hazardous)", "LC (Major)", "LD (Minor)"], half=True, required=True),
            ]},
        ]},
        {"key": "2", "name": "Phase 2: Planning", "steps": [
            {"name": "Step 3: M&S Plan", "fields": [
                head("pirt_head", "Phenomenon Identification Ranking Table (PIRT)",
                     "Identify the physical phenomena that influence the system behavior and calculation of QoI."),
                {"key": "pirt", "type": "table", "label": "PIRT", "required": True, "config": {"columns": [
                    {"key": "phenomenon", "label": "Physical phenomenon", "type": "text"},
                    {"key": "rank", "label": "Ranking", "type": "dropdown", "options": ["High", "Medium", "Low"]},
                    {"key": "justification", "label": "Justification", "type": "text"}]}},
                link("pirt_sheet", "PIRT data (Google Sheet)"),
                head("model_head", "Conceptual & Mathematical Model Definitions",
                     "Document inclusions, simplifications, and exclusions regarding features, conditions, and phenomena."),
                link("model_sheet", "Model definitions (Google Sheet)"),
                head("spec_head", "Application Model Specification"),
                text("extent", "Computational model extent", half=True), text("part_details", "Part modeling details", half=True),
                text("material", "Part material details", half=True), text("interface", "Interface modeling details", half=True),
                text("bc", "Model initial/boundary conditions", half=True), text("physics", "Physics representation", half=True),
                text("sim_type", "Simulation type and parameters", half=True), text("solver", "Solver type and settings (code)", half=True),
            ]},
            {"name": "Step 4: V&V Plan", "fields": [
                area("verification_plan", "Verification plan", required=True),
                area("validation_plan", "Validation plan", required=True),
                area("acceptance", "Acceptance criteria", required=True),
            ]},
        ]},
        {"key": "3", "name": "Phase 3: Execution", "steps": [
            {"name": "Step 5: Verification", "fields": [area("verification_results", "Verification results", required=True), upload("verification_report", "Verification report")]},
            {"name": "Step 6: Validation", "fields": [area("validation_results", "Validation results", required=True), upload("validation_report", "Validation report")]},
        ]},
        {"key": "4", "name": "Phase 4: Application", "is_terminal": True, "steps": [
            {"name": "Step 7: Application", "fields": [area("application_results", "Application results", required=True), upload("application_report", "Application report")]},
            {"name": "Step 8: Uncertainty", "fields": [area("uncertainty", "Uncertainty quantification")]},
        ]},
    ],
    "transitions": [
        {"from_key": "1", "to_key": "2"}, {"from_key": "2", "to_key": "3"},
        {"from_key": "3", "to_key": "4"},
    ],
}


# Dummy workflow with branching: the risk level chosen in Phase 1 decides the next phase.
#   Medium/High risk -> 2B detailed assessment (conditional path)
#   anything else    -> 2A standard review (default path)
BRANCHING = {
    "title": "Change Request (branching example)",
    "description": "Phase 1 asks for the risk level. Medium or High goes to a detailed assessment, otherwise a quick review. Both then continue to implementation.",
    "phases": [
        {"key": "1", "name": "Phase 1: Request", "is_start": True, "steps": [
            {"name": "Step 1: Change details", "fields": [
                text("title", "Change title", required=True),
                area("description", "Description", "What is changing and why?", True),
                drop("risk_level", "Risk level", ["Low", "Medium", "High"], half=True, required=True),
                {"key": "cost", "type": "number", "label": "Estimated cost", "required": False, "config": {"width": "half", "min": 0}},
            ]},
            {"name": "Step 2: Impact", "fields": [
                area("impact", "Impact on systems and teams", required=True),
            ]},
        ]},
        {"key": "2A", "name": "Phase 2A: Standard review", "steps": [
            {"name": "Step 3: Quick review", "fields": [area("quick_notes", "Reviewer notes", required=True)]},
        ]},
        {"key": "2B", "name": "Phase 2B: Detailed assessment", "steps": [
            {"name": "Step 3: Risk assessment", "fields": [
                head("risks_head", "Risk register", "List each risk and how severe it is."),
                {"key": "risks", "type": "table", "label": "Risks", "required": True, "config": {"columns": [
                    {"key": "risk", "label": "Risk", "type": "text"},
                    {"key": "severity", "label": "Severity", "type": "dropdown", "options": ["High", "Medium", "Low"]},
                    {"key": "mitigation", "label": "Mitigation", "type": "text"}]}},
            ]},
            {"name": "Step 4: Rollback plan", "fields": [area("rollback", "Rollback plan", required=True), upload("rollback_doc", "Supporting document")]},
        ]},
        {"key": "3", "name": "Phase 3: Implementation", "is_terminal": True, "steps": [
            {"name": "Step 5: Implement", "fields": [
                area("impl_notes", "Implementation notes", required=True),
                {"key": "done_on", "type": "date", "label": "Completed on", "required": True, "config": {"width": "half"}},
            ]},
        ]},
    ],
    "transitions": [
        {"from_key": "1", "to_key": "2B", "condition": {"all": [{"field": "risk_level", "op": "in", "value": ["Medium", "High"]}]}},
        {"from_key": "1", "to_key": "2A", "is_default": True},
        {"from_key": "2A", "to_key": "3"},
        {"from_key": "2B", "to_key": "3"},
    ],
}


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_admin(db)
        admin = db.scalar(select(User).where(User.role == "admin"))
        for spec in (M_S, BRANCHING):
            if db.scalar(select(Workflow).where(Workflow.title == spec["title"])):
                print(f"Skipped (already exists): {spec['title']}")
                continue
            wf = Workflow(title=spec["title"], created_by=admin.id)
            db.add(wf)
            db.flush()
            apply_graph(db, wf, WorkflowIn(**spec))
            wf.status, wf.approved_by, wf.approved_at = "approved", admin.id, now()
            db.commit()
            print(f"Created and approved workflow #{wf.id}: {wf.title}")


if __name__ == "__main__":
    main()
