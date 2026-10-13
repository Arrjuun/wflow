from app.conditions import choose, evaluate, validate_graph


def P(key, start=False, end=False, fields=("budget",)):
    return {"key": key, "name": key, "is_start": start, "is_terminal": end,
            "steps": [{"name": "s", "fields": [{"key": f, "label": f, "type": "number", "conditionable": True} for f in fields]}]}


def T(a, b, cond=None, default=False):
    return {"from_key": a, "to_key": b, "condition": cond, "is_default": default}


GT10 = {"all": [{"field": "budget", "op": "gt", "value": 10}]}


def test_evaluate():
    assert evaluate(GT10, {"budget": 25})
    assert not evaluate(GT10, {"budget": 5})
    assert evaluate({"field": "t", "op": "in", "value": ["x", "y"]}, {"t": "y"})
    assert evaluate(None, {})


def test_choose_condition_beats_default_regardless_of_order():
    paths = [T("1", "B", default=True), T("1", "A", GT10)]
    assert choose(paths, {"budget": 50})["to_key"] == "A"
    assert choose(paths, {"budget": 1})["to_key"] == "B"
    assert choose([T("1", "2")], {})["to_key"] == "2"  # single unconditional path


def test_valid_branching_graph():
    phases = [P("1", start=True), P("2A", end=True), P("2B", end=True)]
    assert validate_graph(phases, [T("1", "2A", GT10), T("1", "2B", default=True)]) == []


def test_graph_errors():
    phases = [P("1", start=True), P("2"), P("3", end=True), P("orphan", end=True)]
    errors = " | ".join(validate_graph(phases, [T("1", "2"), T("2", "3", {"all": [{"field": "nope", "op": "eq", "value": 1}]})]))
    assert "orphan" in errors and "nope" in errors and "default" in errors
