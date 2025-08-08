import ast
from typing import Generator, Tuple, Type

from .base import BaseRule


class PathBasedResourceRule(BaseRule):
    CODE = "INF001"
    MESSAGE = "avoid using Path(__file__) or os.path.* for resource loading — use loader"

    def run(self) -> Generator[Tuple[int, int, str, Type["BaseRule"]], None, None]:
        self.visit(self.tree)
        for lineno, col, msg in self.violations:
            yield (lineno, col, f"{self.CODE} {msg}", type(self))

    def visit_Call(self, node: ast.Call):
        if self._is_path_file(node):
            self._report(node, "avoid using Path(__file__)")
        if self._is_os_path_dirname(node):
            self._report(node, "avoid using os.path.dirname(__file__)")
        if self._is_os_path_join_with_file(node):
            self._report(node, "avoid using os.path.join(...) with __file__")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if self._is_path_file_parent(node):
            self._report(node, "avoid accessing Path(__file__).parent")
        self.generic_visit(node)

    def _report(self, node: ast.AST, msg: str):
        self.violations.append((node.lineno, node.col_offset, msg))

    def _is_path_file(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Name)
            and node.func.id == "Path"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "__file__"
        )

    def _is_os_path_dirname(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "dirname"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "path"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "os"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "__file__"
        )

    def _is_os_path_join_with_file(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "path"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "os"
            and any(isinstance(arg, ast.Name) and arg.id == "__file__" for arg in node.args)
        )

    def _is_path_file_parent(self, node: ast.Attribute) -> bool:
        return (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Path"
            and isinstance(node.value.args[0], ast.Name)
            and node.value.args[0].id == "__file__"
            and node.attr == "parent"
        )
