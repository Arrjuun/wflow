"""End-to-end: users, workflow with phases + branching, team gate review, references, archive."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

P = "/api/v1"


def login(client, email, password):
    r = client.post(f"{P}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def ok(r, code=200):
    assert r.status_code == code, r.text
    return r.json()


GRAPH = {
    "title": "Purchase", "description": "",
    "phases": [
        {"key": "1", "name": "Request", "is_start": True, "steps": [
            {"name": "Details", "fields": [
                {"key": "h", "type": "heading", "label": "Basics", "config": {"text": "What and how much"}},
                {"key": "title", "type": "text", "label": "Title", "required": True, "config": {"width": "half"}},
                {"key": "amount", "type": "number", "label": "Amount", "required": True}]},
            {"name": "Risks", "fields": [
                {"key": "pirt", "type": "table", "label": "Risks",
                 "config": {"columns": [{"key": "risk", "label": "Risk"},
                                        {"key": "rank", "label": "Rank", "type": "dropdown", "options": ["High", "Low"]}]}}]}]},
        {"key": "2A", "name": "Small purchase", "is_terminal": True, "steps": [{"name": "Confirm", "fields": []}]},
        {"key": "2B", "name": "Finance review", "steps": [{"name": "Budget", "fields": []}]},
        {"key": "3", "name": "Close-out", "is_terminal": True, "requires_gate": False,
         "steps": [{"name": "Notes", "fields": [{"key": "notes", "type": "textarea", "label": "Notes"}]}]},
    ],
    "transitions": [
        {"from_key": "1", "to_key": "2A", "is_default": True},
        {"from_key": "1", "to_key": "2B", "condition": {"all": [{"field": "amount", "op": "gt", "value": 1000}]}},
        {"from_key": "2B", "to_key": "3"},
    ],
}


def test_full_flow():
    with TestClient(app) as admin:
        login(admin, "admin@example.com", "admin12345")
        people, ids = {}, {}
        for name in ("alice", "bob", "carol", "dan", "eve"):
            c = TestClient(app)
            ok(c.post(f"{P}/auth/register", json={"email": f"{name}@x.com", "name": name, "password": "password123"}), 201)
            people[name] = c
        for u in ok(admin.get(f"{P}/users", params={"status": "pending"})):
            ids[u["name"]] = u["id"]
            ok(admin.post(f"{P}/users/{u['id']}/approve"))
        for name, c in people.items():
            login(c, f"{name}@x.com", "password123")
        alice, bob, carol, dan, eve = (people[n] for n in ("alice", "bob", "carol", "dan", "eve"))

        wf = ok(alice.post(f"{P}/workflows", json={"title": "Purchase"}), 201)
        ok(alice.put(f"{P}/workflows/{wf['id']}", json=GRAPH))
        ok(alice.post(f"{P}/workflows/{wf['id']}/submit"))
        ok(admin.post(f"{P}/workflows/{wf['id']}/approve"))

        # project details are defined by the creator
        details = [{"key": "fem_no", "type": "text", "label": "FEM registration number", "required": True},
                   {"key": "start", "type": "date", "label": "Start date"}]
        r = alice.post(f"{P}/projects", json={"workflow_id": wf["id"], "name": "Laptops", "detail_fields": details,
                                              "detail_values": {}, "members": [{"user_id": ids["bob"], "role": "author"}]})
        assert r.status_code == 422 and "FEM registration number is required" in r.text
        project = ok(alice.post(f"{P}/projects", json={
            "workflow_id": wf["id"], "name": "Laptops", "detail_fields": details,
            "detail_values": {"fem_no": "FEM-26-001", "start": "2026-05-13"},
            "members": [{"user_id": ids["bob"], "role": "author"}, {"user_id": ids["carol"], "role": "approver"}]}), 201)
        assert project["detail_values"]["fem_no"] == "FEM-26-001"
        pid, inst_id = project["id"], project["current_instance_id"]

        # references are not part of approval; only the creator manages them
        ok(alice.post(f"{P}/projects/{pid}/references", json={"title": "Policy", "url": "https://example.com/p"}), 201)
        assert bob.post(f"{P}/projects/{pid}/references", json={"title": "x", "url": "https://a.b"}).status_code == 403

        phase = ok(bob.get(f"{P}/phase-instances/{inst_id}"))
        details_step, risks_step = phase["steps"][0]["id"], phase["steps"][1]["id"]

        # only the project team (authors) or an admin can fill/submit; the creator alone cannot
        assert alice.post(f"{P}/step-instances/{details_step}/submit", json={"values": {"title": "x", "amount": 1}}).status_code == 403
        ok(admin.put(f"{P}/phase-instances/{inst_id}/values", json={"values": {"title": "Draft by admin"}}))

        ok(bob.post(f"{P}/step-instances/{details_step}/submit", json={"values": {"title": "Laptops", "amount": 5000}}))
        assert ok(carol.get(f"{P}/me/actions"))[0]["action"] == "Review Details"
        # only project approvers review steps
        assert dan.post(f"{P}/step-instances/{details_step}/decision", json={"decision": "approved"}).status_code == 403
        ok(carol.post(f"{P}/step-instances/{details_step}/decision", json={"decision": "rejected", "comment": "Add vendor"}))
        ok(bob.post(f"{P}/step-instances/{details_step}/submit", json={"values": {}}))
        ok(carol.post(f"{P}/step-instances/{details_step}/decision", json={"decision": "approved"}))

        # add eve as a second approver and dan as authorizer mid-phase
        ok(alice.put(f"{P}/projects/{pid}/members", json={"members": [
            {"user_id": ids["bob"], "role": "author"}, {"user_id": ids["carol"], "role": "approver"},
            {"user_id": ids["eve"], "role": "approver"}, {"user_id": ids["dan"], "role": "authorizer"}]}))
        ok(bob.post(f"{P}/step-instances/{risks_step}/submit", json={"values": {"pirt": [{"risk": "Delivery", "rank": "High"}]}}))
        ok(carol.post(f"{P}/step-instances/{risks_step}/decision", json={"decision": "approved"}))
        # assert ok(bob.get(f"{P}/phase-instances/{inst_id}"))["steps"][1]["status"] == "submitted"  # eve still to approve
        after = ok(eve.post(f"{P}/step-instances/{risks_step}/decision", json={"decision": "approved"}))
        assert after["status"] == "awaiting_signoff"

        # authorizer (or admin) signs off the gate -> branch to 2B (amount > 1000)
        assert carol.post(f"{P}/phase-instances/{inst_id}/signoff", json={"decision": "approved"}).status_code == 403
        ok(admin.post(f"{P}/phase-instances/{inst_id}/signoff", json={"decision": "approved"}))
        detail = ok(alice.get(f"{P}/projects/{pid}"))
        status = {ph["key"]: ph["status"] for ph in detail["phases"]}
        assert status == {"1": "approved", "2A": "not_started", "2B": "in_progress", "3": "not_started"}
        assert 0 < detail["progress"] < 100

        # 2B: one step, two approvers, sign-off; then lessons learned (no gate) completes the project
        cur = ok(bob.get(f"{P}/phase-instances/{detail['current_instance_id']}"))
        step = cur["steps"][0]["id"]
        ok(bob.post(f"{P}/step-instances/{step}/submit", json={"values": {}}))
        ok(admin.post(f"{P}/step-instances/{step}/decision", json={"decision": "approved"}))  # admin override
        ok(dan.post(f"{P}/phase-instances/{cur['id']}/signoff", json={"decision": "approved"}))
        last = ok(bob.get(f"{P}/phase-instances/{ok(alice.get(f'{P}/projects/{pid}'))['current_instance_id']}"))
        ok(bob.post(f"{P}/step-instances/{last['steps'][0]['id']}/submit", json={"values": {"notes": "Order earlier"}}))
        ok(carol.post(f"{P}/step-instances/{last['steps'][0]['id']}/decision", json={"decision": "approved"}))
        ok(eve.post(f"{P}/step-instances/{last['steps'][0]['id']}/decision", json={"decision": "approved"}))
        done = ok(alice.get(f"{P}/projects/{pid}"))
        assert done["status"] == "completed" and done["progress"] == 100
        assert ok(alice.post(f"{P}/projects/{pid}/archive"))["status"] == "archived"
