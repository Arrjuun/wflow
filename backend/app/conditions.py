"""Pure logic (no database): condition evaluation and workflow graph validation."""

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
    op, actual, expected = rule.get("op"), values.get(rule.get("field")), rule.get("value")
    if actual is None:
        return False
    if op == "in":
        pool = expected if isinstance(expected, list) else [expected]
        return str(actual) in [str(p) for p in pool]
    if op == "contains":
        return str(expected).lower() in str(actual).lower()
    a, b = _pair(actual, expected)
    return {"eq": a == b, "ne": a != b, "gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}.get(op, False)


def evaluate(condition: dict | None, values: dict) -> bool:
    """condition: None | {"all": [rule,...]} | {"any": [rule,...]} | a single rule."""
    if not condition:
        return True
    if "all" in condition:
        return all(eval_rule(r, values) for r in condition["all"])
    if "any" in condition:
        return any(eval_rule(r, values) for r in condition["any"])
    return eval_rule(condition, values)


def _rules(condition):
    if not condition:
        return []
    return condition.get("all") or condition.get("any") or ([condition] if "field" in condition else [])


def is_default(t: dict, outgoing: list[dict]) -> bool:
    """A path is the default if marked so, or if it is the only path and has no condition."""
    return bool(t.get("is_default")) or (len(outgoing) == 1 and not t.get("condition"))


def choose(outgoing: list[dict], values: dict):
    """Conditional paths win (in list order); otherwise the default path."""
    for t in outgoing:
        if not is_default(t, outgoing) and evaluate(t.get("condition"), values):
            return t
    return next((t for t in outgoing if is_default(t, outgoing)), None)


def validate_graph(phases: list[dict], transitions: list[dict]) -> list[str]:
    """phases: [{key, name, is_start, is_terminal, steps:[{name, fields:[{key,label,type,conditionable}]}]}]
    transitions: [{from_key, to_key, condition, is_default}]"""
    errors: list[str] = []
    if not phases:
        return ["Add at least one phase."]
    keys = [p["key"] for p in phases]
    if len(set(keys)) != len(keys):
        errors.append("Phase keys must be unique.")
    by_key = {p["key"]: p for p in phases}
    starts = [p for p in phases if p["is_start"]]
    if len(starts) != 1:
        errors.append("Exactly one phase must be marked as the start phase.")
    if not any(p["is_terminal"] for p in phases):
        errors.append("Mark at least one phase as an end phase.")

    out: dict[str, list[dict]] = {k: [] for k in by_key}
    for t in transitions:
        if t["from_key"] not in by_key or t["to_key"] not in by_key:
            errors.append("A path points to a phase that does not exist.")
            continue
        out[t["from_key"]].append(t)

    for p in phases:
        label = f"Phase {p['key']} ({p['name']})"
        fields = [f for s in p.get("steps", []) for f in s.get("fields", [])]
        if not p.get("steps"):
            errors.append(f"{label} needs at least one step.")
        fkeys = [f["key"] for f in fields]
        if len(set(fkeys)) != len(fkeys):
            errors.append(f"{label}: field keys must be unique within the phase.")
        outgoing = out[p["key"]]
        if p["is_terminal"]:
            if outgoing:
                errors.append(f"{label} is an end phase and cannot have outgoing paths.")
            continue
        if not outgoing:
            errors.append(f"{label} has no outgoing path.")
            continue
        defaults = [t for t in outgoing if is_default(t, outgoing)]
        if len(defaults) != 1:
            errors.append(f"{label} needs exactly one default path (found {len(defaults)}).")
        usable = {f["key"] for f in fields if f.get("conditionable", True)}
        for t in outgoing:
            if t in defaults:
                continue
            if not t.get("condition"):
                errors.append(f"{label}: the path to {t['to_key']} needs a condition or must be the default.")
            for r in _rules(t.get("condition")):
                if r.get("op") not in OPS:
                    errors.append(f"{label}: unknown operator '{r.get('op')}'.")
                if r.get("field") not in usable:
                    errors.append(f"{label}: condition uses '{r.get('field')}', which is not a usable field in this phase.")

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
                errors.append(f"Phase {k} cannot be reached from the start phase.")
    return errors
