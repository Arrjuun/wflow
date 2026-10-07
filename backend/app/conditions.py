"""Pure logic (no database): condition evaluation and workflow graph validation."""
from typing import Any

OPS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _pair(a, b):
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        return na, nb
    return str(a), str(b)  # ISO dates compare correctly as strings


def eval_rule(rule: dict, values: dict) -> bool:
    op = rule.get("op")
    actual = values.get(rule.get("field"))
    expected = rule.get("value")
    if actual is None:
        return False
    if op == "in":
        pool = expected if isinstance(expected, list) else [expected]
        return str(actual) in [str(p) for p in pool]
    if op == "contains":
        return str(expected).lower() in str(actual).lower()
    a, b = _pair(actual, expected)
    return {
        "eq": a == b, "ne": a != b, "gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b,
    }.get(op, False)


def evaluate(condition: dict | None, values: dict) -> bool:
    """condition: None | {"all": [rule,...]} | {"any": [rule,...]} | a single rule."""
    if not condition:
        return True
    if "all" in condition:
        return all(eval_rule(r, values) for r in condition["all"])
    if "any" in condition:
        return any(eval_rule(r, values) for r in condition["any"])
    return eval_rule(condition, values)


def _rules(condition: dict | None) -> list[dict]:
    if not condition:
        return []
    return condition.get("all") or condition.get("any") or ([condition] if "field" in condition else [])


def effective_default(outgoing: list[dict]) -> list[dict]:
    """Transitions that act as the fallback: flagged default, or the only unconditional one."""
    flagged = [t for t in outgoing if t.get("is_default")]
    if flagged:
        return flagged
    return [t for t in outgoing if len(outgoing) == 1 and not t.get("condition")]


def validate_graph(steps: list[dict], transitions: list[dict]) -> list[str]:
    """steps: [{key, name, is_start, is_terminal, fields:[{key,label}]}]
    transitions: [{from_key, to_key, condition, is_default}]"""
    errors: list[str] = []
    if not steps:
        return ["Add at least one step."]
    keys = [s["key"] for s in steps]
    if len(set(keys)) != len(keys):
        errors.append("Step keys must be unique.")
    by_key = {s["key"]: s for s in steps}

    starts = [s for s in steps if s["is_start"]]
    if len(starts) != 1:
        errors.append("Exactly one step must be marked as the start step.")
    if not any(s["is_terminal"] for s in steps):
        errors.append("Mark at least one step as an end step.")

    out: dict[str, list[dict]] = {k: [] for k in by_key}
    for t in transitions:
        if t["from_key"] not in by_key or t["to_key"] not in by_key:
            errors.append("A transition points to a step that does not exist.")
            continue
        out[t["from_key"]].append(t)

    for s in steps:
        k, outgoing = s["key"], out[s["key"]]
        label = f"Step {k} ({s['name']})"
        if s["is_terminal"]:
            if outgoing:
                errors.append(f"{label} is an end step and cannot have outgoing transitions.")
            continue
        if not outgoing:
            errors.append(f"{label} has no outgoing transition.")
            continue
        defaults = effective_default(outgoing)
        if len(defaults) != 1:
            errors.append(f"{label} needs exactly one default transition (found {len(defaults)}).")
        field_keys = {f["key"] for f in s.get("fields", [])}
        for t in outgoing:
            if t not in defaults and not t.get("condition"):
                errors.append(f"{label}: a non-default transition to {t['to_key']} needs a condition.")
            for r in _rules(t.get("condition")):
                if r.get("op") not in OPS:
                    errors.append(f"{label}: unknown operator '{r.get('op')}'.")
                if r.get("field") not in field_keys:
                    errors.append(f"{label}: condition uses field '{r.get('field')}' which is not on this step.")

    if len(starts) == 1:
        seen, stack = set(), [starts[0]["key"]]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(t["to_key"] for t in out.get(cur, []) if t["to_key"] in by_key)
        for k in keys:
            if k not in seen:
                errors.append(f"Step {k} cannot be reached from the start step.")
    return errors
