import ast
from typing import Generator, Tuple, Type

from .base import BaseRule


class DictReturnInLoadRule(BaseRule):
    CODE = "INF002"
    MESSAGE = "load_* functions must return typed models — not dict[str, Any]"

    def run(self) -> Generator[Tuple[int, int, str, Type["BaseRule"]], None, None]:
        self.visit(self.tree)
        for lineno, col, msg in self.violations:
            yield (lineno, col, f"{self.CODE} {msg}", type(self))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name.startswith("load_") and self._returns_unmodeled_dict(node):
            self._report(node, "load_* functions must return a Pydantic model, not dict[str, Any]")
        self.generic_visit(node)

    def _returns_unmodeled_dict(self, node: ast.FunctionDef) -> bool:
        """Detect if return type is a dict/mapping with a non-DTO value type."""
        annotation = node.returns
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name) and annotation.value.id in {"dict", "Dict", "Mapping"}:
                if isinstance(annotation.slice, ast.Index):  # Python <3.9
                    slice_value = annotation.slice.value
                else:
                    slice_value = annotation.slice
                if isinstance(slice_value, ast.Tuple) and len(slice_value.elts) == 2:
                    _, value = slice_value.elts
                    if isinstance(value, ast.Name) and not value.id.endswith("DTO"):
                        return True
        return False

    def _report(self, node: ast.FunctionDef, msg: str):
        self.violations.append((node.lineno, node.col_offset, msg))
