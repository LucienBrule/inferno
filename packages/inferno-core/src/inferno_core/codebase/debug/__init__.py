import logging
import os
from functools import wraps
from typing import List

from pydantic import BaseModel

_SPY_LOGGER = logging.getLogger("inferno.spy")


def spy_enabled() -> bool:
    val = os.getenv("INFERNO_SPY", "0")
    return str(val).lower() not in {"", "0", "false", "no"}


def spy_trace(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if spy_enabled():
            _SPY_LOGGER.debug("Entering %s", func.__qualname__)
        result = func(*args, **kwargs)
        if spy_enabled():
            _SPY_LOGGER.debug("Exiting %s", func.__qualname__)
        return result
    return wrapper


class BaseSpyObject:
    @spy_trace
    def __init__(self, **kwargs):
        self.data = kwargs

    @spy_trace
    def __getitem__(self, key):
        return self.data[key]

    @spy_trace
    def __setitem__(self, key, value):
        self.data[key] = value

    @spy_trace
    def __contains__(self, key):
        return key in self.data

    @spy_trace
    def get(self, key, default=None):
        return self.data.get(key, default)

    @spy_trace
    def keys(self):
        return self.data.keys()

    @spy_trace
    def values(self):
        return self.data.values()

    @spy_trace
    def items(self):
        return self.data.items()

    @staticmethod
    def from_any(obj, default=None):
        """Recursively convert various typed objects into plain Python dict/list primitives.
        Supports Pydantic v2 (model_dump), Pydantic v1 (dict), dataclasses, and collections.
        """
        from dataclasses import is_dataclass, asdict
        try:
            from pydantic import BaseModel as _PydBase
        except Exception:
            _PydBase = BaseModel  # already imported above

        if obj is None:
            return default
        if isinstance(obj, BaseSpyObject):
            return obj.data
        if isinstance(obj, _PydBase):
            try:
                return {k: BaseSpyObject.from_any(v) for k, v in obj.model_dump(mode="python").items()}
            except TypeError:
                return {k: BaseSpyObject.from_any(v) for k, v in obj.model_dump().items()}
        if is_dataclass(obj):
            return {k: BaseSpyObject.from_any(v) for k, v in asdict(obj).items()}
        if isinstance(obj, dict):
            return {k: BaseSpyObject.from_any(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            t = type(obj)
            return t(BaseSpyObject.from_any(v) for v in obj)
        # Pydantic v1 compatibility
        if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
            try:
                return {k: BaseSpyObject.from_any(v) for k, v in obj.dict().items()}
            except Exception:
                pass
        return obj


class SpyCablePolicy(BaseSpyObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SpyCableBom(BaseSpyObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SpyCableLink(BaseSpyObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SpyCableTors(BaseSpyObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SpyCableNodes(BaseSpyObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SpyCableTopology(BaseSpyObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


SpyCableLinkList = List[SpyCableLink]
