from app.conditions import evaluate, validate_graph


def S(key, start=False, end=False, fields=("budget",)):
    return {"key": key, "name": key, "is_start": start, "is_terminal": end,
            "fields": [{"key": f, "label": f} for f in fields]}


def T(a, b, cond=None, default=False):
    return {"from_key": a, "to_key": b, "condition": cond, "is_default": default}


def test_evaluate_numeric_and_groups():
    assert evaluate({"all": [{"field": "budget", "op": "gt", "value": 10000}]}, {"budget": 25000})
    assert not evaluate({"all": [{"field": "budget", "op": "gt", "value": 10000}]}, {"budget": 900})
    assert evaluate({"any": [{"field": "t", "op": "eq", "value": "a"}, {"field": "t", "op": "eq", "value": "b"}]}, {"t": "b"})
    assert evaluate({"field": "t", "op": "in", "value": ["x", "y"]}, {"t": "y"})
    assert evaluate(None, {})
    assert not evaluate({"field": "missing", "op": "eq", "value": 1}, {})


def test_valid_branching_graph():
    steps = [S("4", start=True), S("5A", end=True), S("5B", end=True)]
    tr = [T("4", "5A", {"all": [{"field": "budget", "op": "gt", "value": 10}]}), T("4", "5B", default=True)]
    assert validate_graph(steps, tr) == []


def test_graph_errors():
    steps = [S("1", start=True), S("2"), S("3", end=True), S("orphan", end=True)]
    tr = [T("1", "2"), T("2", "3", {"all": [{"field": "nope", "op": "eq", "value": 1}]})]
    errors = " | ".join(validate_graph(steps, tr))
    assert "orphan" in errors            # unreachable
    assert "nope" in errors              # unknown condition field
    assert "default" in errors           # step 2 has only a conditional transition
