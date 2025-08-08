import ast
from typing import Generator, Tuple, Type

from .base import BaseRule


class NoDirectResourceImportRule(BaseRule):
    CODE = "INF004"
    MESSAGE = "do not import inferno_core.data.resources — use loader interface"

    def run(self) -> Generator[Tuple[int, int, str, Type["BaseRule"]], None, None]:
        self.visit(self.tree)
        for lineno, col, msg in self.violations:
            yield (lineno, col, f"{self.CODE} {msg}", type(self))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and node.module.startswith("glyphsieve.resources"):
            self._report(node, self.MESSAGE)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name.startswith("glyphsieve.resources"):
                self._report(node, self.MESSAGE)
        self.generic_visit(node)

    def _report(self, node: ast.AST, msg: str):
        self.violations.append((node.lineno, node.col_offset, msg))
