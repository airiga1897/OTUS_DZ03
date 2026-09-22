"""Проверки запуска без доступа к облаку: журнал и сохранение кода ошибки."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


class DeploymentResultTest(unittest.TestCase):
    def test_success_and_failure_are_preserved(self):
        source = Path(__file__).resolve().parents[1] / "scripts/apply_deploy.py"
        spec = importlib.util.spec_from_file_location("apply_deploy", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for expected in (0, 7):
            with self.subTest(exit_code=expected), tempfile.TemporaryDirectory() as folder:
                module.ROOT = Path(folder)
                scripts = module.ROOT / "scripts"
                scripts.mkdir()
                (scripts / "controller.py").write_text(
                    f"import sys\nprint('Проверка stdout')\nprint('Проверка stderr', file=sys.stderr)\nsys.exit({expected})\n",
                    encoding="utf-8",
                )
                self.assertEqual(module.main(), expected)
                logs = list((module.ROOT / ".local/logs").glob("deploy-*.log"))
                self.assertEqual(len(logs), 1)
                content = logs[0].read_text(encoding="utf-8")
                self.assertIn("Проверка stdout", content)
                self.assertIn("Проверка stderr", content)


if __name__ == "__main__":
    unittest.main()
