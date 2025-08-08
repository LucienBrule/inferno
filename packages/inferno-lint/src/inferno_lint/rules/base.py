import ast
from abc import ABC, abstractmethod
from typing import Generator, Tuple, Type


class BaseRule(ast.NodeVisitor, ABC):
    CODE: str = ""
    MESSAGE: str = ""

    def __init__(self, tree: ast.AST, filename: str):
        self.tree = tree
        self.filename = filename
        self.violations: list[Tuple[int, int, str]] = []

    @abstractmethod
    def run(self) -> Generator[Tuple[int, int, str, Type["BaseRule"]], None, None]:
        """Scan the AST and yield violations."""
        ...
