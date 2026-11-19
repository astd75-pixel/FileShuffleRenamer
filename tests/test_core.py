import tempfile
import unittest
from pathlib import Path
from SRC.renamer_core import build_plan, execute_plan, undo_last, RenameError


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for name in ["яблоко.jpg", "photo.png", "документ.pdf", "very_long_" + "x"*100 + ".txt"]:
            (self.folder / name).write_bytes(b"content")

    def tearDown(self):
        self.tmp.cleanup()

    def test_extensions_and_unique_numbering(self):
        plan = build_plan(self.folder, 100, 5, "File_", "_")
        self.assertEqual(len(plan), 4)
        self.assertEqual({p.target.suffix for p in plan}, {".jpg", ".png", ".pdf", ".txt"})
        self.assertEqual({p.target.stem for p in plan}, {"File_100_", "File_105_", "File_110_", "File_115_"})

    def test_execute_and_undo_preserves_bytes(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir() if p.is_file()}
        plan = build_plan(self.folder, rng=__import__("random").Random(2))
        execute_plan(plan)
        self.assertEqual(len(list(self.folder.glob("*"))), 5)  # 4 renamed files + journal folder
        undo_last(self.folder)
        after = {p.name: p.read_bytes() for p in self.folder.iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_collision(self):
        for n in range(1, 5):
            (self.folder / f"{n}_.jpg").mkdir()
        with self.assertRaises(RenameError):
            build_plan(self.folder)

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(build_plan(Path(empty)), [])

    def test_zero_step(self):
        with self.assertRaises(RenameError):
            build_plan(self.folder, step=0)


if __name__ == "__main__":
    unittest.main()
