import warnings
from pathlib import Path
from typing import Any, Generic, TypeVar, overload

import yaml
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic import BaseModel as GenericModel

T = TypeVar("T")
U = TypeVar("U", bound=BaseModel)


class MapOf(GenericModel, Generic[U]):
    root: dict[str, U]


# -------------------------------
# Internal raw YAML reader (single source of truth)
# -------------------------------


def _read_yaml_raw(path: Path | str) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"Unable to decode UTF-8 in {p}: {e}") from e

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {p}: {e}") from e

    if data is None:
        raise ValueError(f"Empty YAML file: {p}")

    return data


# -------------------------------
# Public typed YAML loader (preferred)
# -------------------------------


@overload
def load_yaml_typed[T](path: Path | str, *, adapter: TypeAdapter[T]) -> T: ...


@overload
def load_yaml_typed[T](path: Path | str, *, model: type[T]) -> T: ...


def load_yaml_typed(
    path: Path | str,
    *,
    adapter: TypeAdapter[T] | None = None,
    model: type[T] | None = None,
) -> T:
    """Read YAML and validate/parse it into a typed object using Pydantic v2.

    Exactly one of {adapter, model} must be supplied.

    Example (single model):
        load_yaml_typed("doctrine/site.yaml", model=SiteRec)

    Example (list of items):
        load_yaml_typed("doctrine/naming/nodes.yaml", adapter=TypeAdapter(list[NodeRec]))
    """
    if (adapter is None) == (model is None):
        raise ValueError("Provide exactly one of 'adapter' or 'model'.")

    data = _read_yaml_raw(path)

    try:
        if adapter is not None:
            return adapter.validate_python(data)
        # model path
        return TypeAdapter(model).validate_python(data)  # type: ignore[arg-type]
    except ValidationError as e:
        # Normalize error so callers see the file path in the message
        raise ValueError(f"Invalid structure in {path}: {e}") from e


# -------------------------------
# Convenience helpers for common shapes
# -------------------------------


def load_yaml_list[U](path: Path | str, item_model: type[U]) -> list[U]:
    """Load a YAML list of objects into List[item_model]."""
    return load_yaml_typed(path, adapter=TypeAdapter(list[item_model]))  # type: ignore[index]


def load_yaml_dict_values[U: BaseModel](path: Path | str, value_model: type[U]) -> MapOf[U]:
    """Load a YAML mapping[str, object] into a typed Pydantic model wrapping the mapping as `.root` property.

    Returns:
        MapOf[U]: A Pydantic model with `.root` containing the mapping of str to value_model.
    """
    data = load_yaml_typed(path, adapter=TypeAdapter(dict[str, value_model]))  # type: ignore[index]
    return MapOf[U](root=data)


# -------------------------------
# Legacy helper (deprecated) — keeps older call-sites working for now
# -------------------------------


def _deprecated(reason: str):
    def deco(fn):
        def wrapped(*args, **kwargs):
            warnings.warn(
                f"{fn.__name__} is deprecated: {reason}",
                category=DeprecationWarning,
                stacklevel=2,
            )
            # Also print a visible line to make it easy to grep in CI logs
            try:
                print(f"[DEPRECATED] {fn.__name__} called with args={args}, kwargs={kwargs}")
            except Exception:
                # printing should never break execution
                pass
            return fn(*args, **kwargs)

        wrapped.__doc__ = (fn.__doc__ or "") + "\n\nDEPRECATED: " + reason
        return wrapped

    return deco


@_deprecated("Use load_yaml_typed()/load_yaml_list()/load_yaml_dict_values instead.")
def load_yaml_file(path: Path | str):
    """Legacy, untyped YAML loader. Prefer typed loaders above."""
    return _read_yaml_raw(path)
