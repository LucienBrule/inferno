import ast
from typing import Generator, Tuple, Type

from .base import BaseRule


class ModelOutsideModelsRule(BaseRule):
    CODE = "INF003"
    MESSAGE = "Pydantic models must be defined in a module path containing `/models/`"

    def run(self) -> Generator[Tuple[int, int, str, Type["BaseRule"]], None, None]:
        self.visit(self.tree)
        for lineno, col, msg in self.violations:
            yield (lineno, col, f"{self.CODE} {msg}", type(self))

    def visit_ClassDef(self, node: ast.ClassDef):
        if self._inherits_from_basemodel(node):
            if "/models/" not in self.filename.replace("\\", "/"):
                self._report(node, "model defined outside any /models/ directory")
        self.generic_visit(node)

    def _inherits_from_basemodel(self, node: ast.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
        return False

    def _report(self, node: ast.ClassDef, msg: str):
        self.violations.append((node.lineno, node.col_offset, msg))
