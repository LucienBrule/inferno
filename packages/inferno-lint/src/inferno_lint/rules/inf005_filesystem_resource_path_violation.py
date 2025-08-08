import ast
from typing import Generator, Tuple, Type

from .base import BaseRule


class FilesystemResourcePathViolationRule(BaseRule):
    CODE = "INF005"
    MESSAGE = "do not hardcode paths to glyphsieve/resources — use resource loader"

    def run(self) -> Generator[Tuple[int, int, str, Type["BaseRule"]], None, None]:
        self.visit(self.tree)
        for lineno, col, msg in self.violations:
            yield (lineno, col, f"{self.CODE} {msg}", type(self))

    def visit_Call(self, node: ast.Call):
        if self._is_path_with_hardcoded_resource(node):
            self._report(node)
        self.generic_visit(node)

    def _is_path_with_hardcoded_resource(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name) and node.func.id == "Path":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                val = str(node.args[0].value)
                return "glyphsieve/resources" in val or "glyphsieve/src/glyphsieve/resources" in val
        return False

    def _report(self, node: ast.AST):
        self.violations.append((node.lineno, node.col_offset, self.MESSAGE))
