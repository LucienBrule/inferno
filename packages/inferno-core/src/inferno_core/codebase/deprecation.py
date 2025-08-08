"""
Rich deprecation decorator for Inferno.

Usage:

    from inferno_core.codebase.deprecation import deprecated

    @deprecated(
        message="Use load_yaml_typed() instead.",
        since="2025.08",
        alternative="inferno_core.data.loader.load_yaml_typed",
        remove_in="2026.01",
    )
    def old_loader(path: Path) -> dict[str, object]:
        ...

Environment flags (all optional):

    INFERNO_DEPRECATION_MODE = "warn" | "error" | "silent"
        Default: "warn". Controls whether we warn, raise, or remain silent.

    INFERNO_DEPRECATION_VERBOSE = "0" | "1"
        Default: "0". If "1", include detailed call info.

    INFERNO_DEPRECATION_PRINT_ARGS = "0" | "1"
        Default: "1" if VERBOSE else "0". Include argument names, values, and types.

    INFERNO_DEPRECATION_PRINT_RETURN = "0" | "1"
        Default: "0". If "1", include return value and type (sync functions only).

    INFERNO_DEPRECATION_PRINT_STACK = "0" | "1"
        Default: "0". If "1", include a call stack.

    INFERNO_DEPRECATION_EMIT_ONCE = "0" | "1"
        Default: "1". If "1", suppress repeated messages for the same function.

    INFERNO_DEPRECATION_SAMPLE = float in [0.0, 1.0]
        Default: "1.0". Probability to emit message per call (sampling).

Notes:
- Return capture is best-effort. We do not attempt to iterate generators or
  await coroutines to capture their *eventual* values; for async functions we
  decorate the coroutine factory and log at call-time. Set PRINT_RETURN for
  sync direct-return functions only.
- The decorator integrates with the Python warnings system using
  DeprecationWarning (mode="warn") and can raise a RuntimeError (mode="error").
"""

from dataclasses import dataclass
from functools import wraps
import inspect
import logging
import os
import random
import traceback
import types
import warnings
from typing import Any, Callable, ParamSpec, TypeVar, overload, cast

P = ParamSpec("P")
R = TypeVar("R")

__all__ = [
    "deprecated",
    "DeprecationConfig",
    "configure_deprecation_logger",
]

_LOGGER_NAME = "inferno.deprecation"
_logger = logging.getLogger(_LOGGER_NAME)


def configure_deprecation_logger(level: int = logging.WARNING) -> None:
    """
    Ensure the deprecation logger has a handler in case the app didn't configure logging.
    Safe to call multiple times.
    """
    if not _logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
    _logger.setLevel(level)


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        out = float(val)
        if out < 0.0:
            return 0.0
        if out > 1.0:
            return 1.0
        return out
    except Exception:
        return default


@dataclass(frozen=True)
class DeprecationConfig:
    mode: str = "warn"  # "warn" | "error" | "silent"
    verbose: bool = False
    print_args: bool = False
    print_return: bool = False
    print_stack: bool = False
    emit_once: bool = True
    sample: float = 1.0

    @classmethod
    def from_env(cls) -> "DeprecationConfig":
        mode = os.getenv("INFERNO_DEPRECATION_MODE", "warn").strip().lower()
        if mode not in {"warn", "error", "silent"}:
            mode = "warn"
        verbose = _env_bool("INFERNO_DEPRECATION_VERBOSE", False)
        print_args = _env_bool("INFERNO_DEPRECATION_PRINT_ARGS", verbose)
        print_return = _env_bool("INFERNO_DEPRECATION_PRINT_RETURN", False)
        print_stack = _env_bool("INFERNO_DEPRECATION_PRINT_STACK", False)
        emit_once = _env_bool("INFERNO_DEPRECATION_EMIT_ONCE", True)
        sample = _env_float("INFERNO_DEPRECATION_SAMPLE", 1.0)
        return cls(
            mode=mode,
            verbose=verbose,
            print_args=print_args,
            print_return=print_return,
            print_stack=print_stack,
            emit_once=emit_once,
            sample=sample,
        )


# Track functions we've already emitted for (when emit_once is True).
_EMITTED: "set[int]" = set()


def _format_value(v: Any, maxlen: int = 200) -> str:
    try:
        s = repr(v)
    except Exception:
        s = f"<unrepr {type(v).__name__}>"
    if len(s) > maxlen:
        s = s[: maxlen - 3] + "..."
    return s


def _format_call_details(
    func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any], cfg: DeprecationConfig
) -> str:
    parts: list[str] = []
    qualname = getattr(func, "__qualname__", getattr(func, "__name__", "<function>"))
    filename = getattr(func, "__code__", None).co_filename if hasattr(func, "__code__") else "<unknown>"
    lineno = getattr(func, "__code__", None).co_firstlineno if hasattr(func, "__code__") else -1
    parts.append(f"callsite: {qualname} ({filename}:{lineno})")
    if cfg.print_args:
        try:
            sig = inspect.signature(func)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            arg_lines: list[str] = []
            for name, value in bound.arguments.items():
                arg_lines.append(f"  - {name}: {_format_value(value)}  :: {type(value).__name__}")
            if arg_lines:
                parts.append("args:")
                parts.extend(arg_lines)
        except Exception as e:
            parts.append(f"args: <failed to inspect: {e}>")
    if cfg.print_stack:
        # exclude the decorator frames by trimming the last few frames
        stack = "".join(traceback.format_stack(limit=12))
        parts.append("stack:")
        parts.append(stack.rstrip())
    return "\n".join(parts)


def _format_return_details(value: Any) -> str:
    return f"return: {_format_value(value)}  :: {type(value).__name__}"


def _build_header(message: str | None, since: str | None, alternative: str | None, remove_in: str | None) -> str:
    chunks: list[str] = ["DEPRECATION:"]
    if message:
        chunks.append(message)
    if since:
        chunks.append(f"(since {since})")
    if alternative:
        chunks.append(f"→ use {alternative}")
    if remove_in:
        chunks.append(f"(will be removed in {remove_in})")
    return " ".join(chunks)


@overload
def deprecated(
    message: str | None = ...,
    *,
    since: str | None = ...,
    alternative: str | None = ...,
    remove_in: str | None = ...,
    emit_once: bool | None = ...,
    mode: str | None = ...,
    verbose: bool | None = ...,
    print_args: bool | None = ...,
    print_return: bool | None = ...,
    print_stack: bool | None = ...,
    sample: float | None = ...,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


# No bare @deprecated without parentheses to avoid ambiguous defaults.


def deprecated(
    message: str | None = None,
    *,
    since: str | None = None,
    alternative: str | None = None,
    remove_in: str | None = None,
    emit_once: bool | None = None,
    mode: str | None = None,
    verbose: bool | None = None,
    print_args: bool | None = None,
    print_return: bool | None = None,
    print_stack: bool | None = None,
    sample: float | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorate a function to mark it deprecated with rich, configurable emission.

    The effective behavior is the merge of explicit kwargs and environment config.
    """
    env_cfg = DeprecationConfig.from_env()
    eff_cfg = DeprecationConfig(
        mode=mode or env_cfg.mode,
        verbose=env_cfg.verbose if verbose is None else verbose,
        print_args=env_cfg.print_args if print_args is None else print_args,
        print_return=env_cfg.print_return if print_return is None else print_return,
        print_stack=env_cfg.print_stack if print_stack is None else print_stack,
        emit_once=env_cfg.emit_once if emit_once is None else emit_once,
        sample=env_cfg.sample if sample is None else sample,
    )

    configure_deprecation_logger()  # ensure visibility

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        func_id = id(func)
        header = _build_header(message, since, alternative, remove_in)

        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Sampling & once-per-func gating
            should_emit = (random.random() <= eff_cfg.sample) and (not eff_cfg.emit_once or func_id not in _EMITTED)
            if should_emit and eff_cfg.emit_once:
                _EMITTED.add(func_id)

            if should_emit and eff_cfg.mode != "silent":
                details = _format_call_details(func, args, kwargs, eff_cfg)
                msg_lines = [header, details]

                if eff_cfg.mode == "warn":
                    warnings.warn(header, category=DeprecationWarning, stacklevel=2)
                    if eff_cfg.verbose:
                        _logger.warning("\n".join(msg_lines))
                elif eff_cfg.mode == "error":
                    _logger.error("\n".join(msg_lines))
                    raise RuntimeError(header)

            result = func(*args, **kwargs)

            if should_emit and eff_cfg.mode != "silent" and eff_cfg.print_return and not is_async:
                try:
                    _logger.warning(_format_return_details(result))
                except Exception:
                    # best-effort; never break the function
                    pass

            return cast(R, result)

        if is_async:
            # Wrap async separately to avoid awaiting inside wrapper.
            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                should_emit = (random.random() <= eff_cfg.sample) and (not eff_cfg.emit_once or func_id not in _EMITTED)
                if should_emit and eff_cfg.emit_once:
                    _EMITTED.add(func_id)

                if should_emit and eff_cfg.mode != "silent":
                    details = _format_call_details(func, args, kwargs, eff_cfg)
                    msg_lines = [header, details]
                    if eff_cfg.mode == "warn":
                        warnings.warn(header, category=DeprecationWarning, stacklevel=2)
                        if eff_cfg.verbose:
                            _logger.warning("\n".join(msg_lines))
                    elif eff_cfg.mode == "error":
                        _logger.error("\n".join(msg_lines))
                        raise RuntimeError(header)

                result = await cast(types.CoroutineType, func(*args, **kwargs))  # type: ignore[misc]
                # We do not log return value for async to avoid awaiting twice / side effects.
                return cast(R, result)

            return cast(Callable[P, R], async_wrapper)

        return cast(Callable[P, R], wrapper)

    return decorator
