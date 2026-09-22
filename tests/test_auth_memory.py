"""Проверки авторизации без облака и настоящих credentials."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import yc_auth
import tf

TOKEN = "a" * 100


class MemoryAuthTests(unittest.TestCase):
    def test_cli_token_is_captured_without_output_or_file_write(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(yc_auth.subprocess, "run") as run, patch.object(Path, "write_text") as write, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess([], 0, TOKEN + "\n", "")
            self.assertEqual(yc_auth.get_token(), TOKEN)
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertIn("--no-browser", run.call_args.args[0])
            write.assert_not_called()
        self.assertEqual(output.getvalue(), "")

    def test_inherited_token_does_not_call_cli(self):
        with patch.dict(os.environ, {"YC_TOKEN": TOKEN}), patch.object(yc_auth.subprocess, "run") as run:
            self.assertEqual(yc_auth.get_token(), TOKEN)
            run.assert_not_called()

    def test_error_does_not_disclose_cli_output(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(yc_auth.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 1, TOKEN, TOKEN)
            with self.assertRaises(SystemExit) as error:
                yc_auth.get_token()
            self.assertNotIn(TOKEN, str(error.exception))

    def test_apply_passes_token_only_to_child_and_preserves_exit_code(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["tf.py", "apply", "plan.tfplan"]), patch.object(tf, "get_token", return_value=TOKEN), patch.object(tf.subprocess, "call", return_value=7) as call:
            self.assertEqual(tf.main(), 7)
            self.assertEqual(call.call_args.kwargs["env"]["YC_TOKEN"], TOKEN)
            self.assertNotIn("YC_TOKEN", os.environ)
            self.assertNotIn(TOKEN, str(call.call_args.args))

    def test_output_does_not_require_cloud_auth(self):
        with patch.object(sys, "argv", ["tf.py", "output"]), patch.object(tf, "get_token") as auth, patch.object(tf.subprocess, "call", return_value=0):
            self.assertEqual(tf.main(), 0)
            auth.assert_not_called()


if __name__ == "__main__":
    unittest.main()
