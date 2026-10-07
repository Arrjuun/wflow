"""Field type registry.

To add a new field type: subclass FieldType, decorate with @register.
Values are stored as JSON, so no database migration is needed.
The frontend needs a matching entry in src/fields/registry.jsx.
"""
from datetime import date
from urllib.parse import urlparse


class FieldError(ValueError):
    pass


class FieldType:
    name = ""
    label = ""

    def validate_config(self, config: dict) -> dict:
        return config or {}

    def clean_value(self, value, config: dict, ctx: dict):
        """Return the normalized value to store, or raise FieldError."""
        return value


REGISTRY: dict[str, FieldType] = {}


def register(cls):
    REGISTRY[cls.name] = cls()
    return cls


def get_type(name: str) -> FieldType:
    if name not in REGISTRY:
        raise FieldError(f"Unknown field type '{name}'")
    return REGISTRY[name]


def list_types() -> list[dict]:
    return [{"name": t.name, "label": t.label} for t in REGISTRY.values()]


@register
class TextField(FieldType):
    name, label = "text", "Short text (title)"

    def validate_config(self, config):
        config = config or {}
        out = {}
        if config.get("max_length"):
            out["max_length"] = int(config["max_length"])
        return out

    def clean_value(self, value, config, ctx):
        if not isinstance(value, str):
            raise FieldError("must be text")
        value = value.strip()
        if config.get("max_length") and len(value) > config["max_length"]:
            raise FieldError(f"must be at most {config['max_length']} characters")
        return value


@register
class TextAreaField(TextField):
    name, label = "textarea", "Long text (description)"


@register
class DropdownField(FieldType):
    name, label = "dropdown", "Drop-down"

    def validate_config(self, config):
        options = [str(o).strip() for o in (config or {}).get("options", []) if str(o).strip()]
        if not options:
            raise FieldError("a drop-down needs at least one option")
        if len(set(options)) != len(options):
            raise FieldError("drop-down options must be unique")
        return {"options": options}

    def clean_value(self, value, config, ctx):
        if value not in config.get("options", []):
            raise FieldError("must be one of the listed options")
        return value


@register
class DateField(FieldType):
    name, label = "date", "Date"

    def clean_value(self, value, config, ctx):
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise FieldError("must be a date (YYYY-MM-DD)")


@register
class UrlField(FieldType):
    name, label = "url", "URL"

    def clean_value(self, value, config, ctx):
        parsed = urlparse(str(value).strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise FieldError("must be a valid http(s) URL")
        return str(value).strip()


@register
class NumberField(FieldType):
    name, label = "number", "Number"

    def validate_config(self, config):
        out = {}
        for k in ("min", "max"):
            if (config or {}).get(k) not in (None, ""):
                out[k] = float(config[k])
        return out

    def clean_value(self, value, config, ctx):
        if isinstance(value, bool):
            raise FieldError("must be a number")
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise FieldError("must be a number")
        if "min" in config and num < config["min"]:
            raise FieldError(f"must be at least {config['min']:g}")
        if "max" in config and num > config["max"]:
            raise FieldError(f"must be at most {config['max']:g}")
        return int(num) if num.is_integer() else num


@register
class FileField(FieldType):
    name, label = "file", "File upload"

    def validate_config(self, config):
        out = {}
        if (config or {}).get("accept"):
            out["accept"] = [str(a).lower().lstrip(".") for a in config["accept"]]
        return out

    def clean_value(self, value, config, ctx):
        from .models import FileAsset  # local import keeps this module dependency-light

        if not isinstance(value, dict) or not isinstance(value.get("file_id"), int):
            raise FieldError("must be an uploaded file")
        asset = ctx["db"].get(FileAsset, value["file_id"])
        if not asset:
            raise FieldError("file not found")
        if config.get("accept"):
            ext = asset.original_name.rsplit(".", 1)[-1].lower() if "." in asset.original_name else ""
            if ext not in config["accept"]:
                raise FieldError(f"file type must be one of: {', '.join(config['accept'])}")
        if ctx.get("instance_id"):
            asset.instance_id = ctx["instance_id"]
        return {"file_id": asset.id, "name": asset.original_name}
