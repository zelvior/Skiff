import unittest
import os
import shutil
import json
import sys
import tempfile

import skiff
import sample_plugins.word_count as word_count


class TestSkiff(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_config_dir = skiff.CONFIG_DIR
        self.orig_config_file = skiff.CONFIG_FILE
        self.orig_history_file = skiff.HISTORY_FILE

        skiff.CONFIG_DIR = os.path.join(self.temp_dir, ".skiff")
        skiff.CONFIG_FILE = os.path.join(skiff.CONFIG_DIR, "config.json")
        skiff.HISTORY_FILE = os.path.join(skiff.CONFIG_DIR, "history.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        skiff.CONFIG_DIR = self.orig_config_dir
        skiff.CONFIG_FILE = self.orig_config_file
        skiff.HISTORY_FILE = self.orig_history_file

    def test_extract_json(self):
        # Plain json
        res = skiff.extract_json('{"tool": "plan", "args": {"steps": ["a"]}}')
        self.assertEqual(res, {"tool": "plan", "args": {"steps": ["a"]}})

        # JSON with markdown fence
        res = skiff.extract_json('```json\n{"tool": "read_file", "args": {"path": "a.txt"}}\n```')
        self.assertEqual(res, {"tool": "read_file", "args": {"path": "a.txt"}})

        # Leading text / thoughts before tool call
        res = skiff.extract_json('I will read the file now.\n{"tool": "read_file", "args": {"path": "a.txt"}}')
        self.assertEqual(res, {"tool": "read_file", "args": {"path": "a.txt"}})

        # Invalid json
        self.assertIsNone(skiff.extract_json('No json here'))

    def test_word_count_plugin(self):
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello world\nsecond line\n")
        res = word_count.run({"path": test_file})
        self.assertTrue(res["ok"])
        self.assertEqual(res["words"], 4)
        self.assertEqual(res["lines"], 2)

        # Empty file check
        empty_file = os.path.join(self.temp_dir, "empty.txt")
        with open(empty_file, "w") as f:
            f.write("")
        res_empty = word_count.run({"path": empty_file})
        self.assertTrue(res_empty["ok"])
        self.assertEqual(res_empty["words"], 0)
        self.assertEqual(res_empty["lines"], 0)

    def test_file_tools_and_backup(self):
        test_file = os.path.join(self.temp_dir, "foo.txt")
        res = skiff.tool_write_file({"path": test_file, "content": "hello"})
        self.assertTrue(res["ok"])

        # Patch file
        res_patch = skiff.tool_patch_file({"path": test_file, "old_str": "hello", "new_str": "world"})
        self.assertTrue(res_patch["ok"])

        # Check backup created
        backup_dir = os.path.join(skiff.CONFIG_DIR, "backups")
        self.assertTrue(os.path.isdir(backup_dir))
        self.assertTrue(len(os.listdir(backup_dir)) > 0)

        # Check file content updated
        res_read = skiff.tool_read_file({"path": test_file})
        self.assertEqual(res_read["content"], "world")

    def test_config_load_save(self):
        cfg = skiff.load_config()
        self.assertEqual(cfg["provider"], "openai")
        cfg["model"] = "custom-model"
        skiff.save_config(cfg)
        loaded = skiff.load_config()
        self.assertEqual(loaded["model"], "custom-model")


if __name__ == "__main__":
    unittest.main()
