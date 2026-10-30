"""Keep the assignment's implementation restrictions visible and verifiable."""

import ast
from pathlib import Path
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "mini_redis"


class AssignmentConstraintTests(unittest.TestCase):
    def test_no_native_key_value_collections_or_replacement_libraries(self):
        for path in SOURCE_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            with self.subTest(module=path.name):
                for node in ast.walk(tree):
                    self.assertNotIsInstance(node, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp))
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, ("dict", "set", "hash"))
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotIn(alias.name.split(".")[0], ("collections", "heapq", "redis"))
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotIn((node.module or "").split(".")[0], ("collections", "heapq", "redis"))

    def test_source_syntax_is_compatible_with_python_3_8(self):
        for path in SOURCE_ROOT.rglob("*.py"):
            with self.subTest(module=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=8)

    def test_required_structures_are_separate_modules(self):
        directory = SOURCE_ROOT / "structures"
        for filename in ("linked_list.py", "hash_map.py", "min_heap.py"):
            self.assertTrue((directory / filename).is_file())


if __name__ == "__main__":
    unittest.main()
