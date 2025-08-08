from ast import AST

from .rules.inf001_pathbased import PathBasedResourceRule
from .rules.inf002_dictload import DictReturnInLoadRule
from .rules.inf003_model_locations import ModelOutsideModelsRule
from .rules.inf004_no_direct_resource_imports import NoDirectResourceImportRule
from .rules.inf005_filesystem_resource_path_violation import (
    FilesystemResourcePathViolationRule,
)


class InfernoChecker:
    def __init__(self, tree: AST, filename: str):
        self.tree = tree
        self.filename = filename

    def run(self):
        rules = [
            PathBasedResourceRule(self.tree, self.filename),
            DictReturnInLoadRule(self.tree, self.filename),
            ModelOutsideModelsRule(self.tree, self.filename),
            NoDirectResourceImportRule(self.tree, self.filename),
            FilesystemResourcePathViolationRule(self.tree, self.filename),
        ]
        for rule in rules:
            yield from rule.run()
