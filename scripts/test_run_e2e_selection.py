"""Selection validation only: these tests never start servers or Playwright."""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("run_e2e_local.py")
MODULE_SPEC = importlib.util.spec_from_file_location("run_e2e_local", MODULE_PATH)
runner = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(runner)


class E2ESelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "frontend/e2e"
        self.directory.mkdir(parents=True)
        self.first = self.directory / "invoice-list.spec.js"
        self.second = self.directory / "clients.spec.js"
        self.first.write_text("", encoding="utf-8")
        self.second.write_text("", encoding="utf-8")

    def test_no_arguments_preserves_full_suite_and_default_timeout(self):
        arguments = runner._parse_arguments([])
        self.assertEqual(arguments.spec, [])
        self.assertIsNone(arguments.timeout_ms)
        self.assertEqual(runner._playwright_command("npx", [], None), ["npx", "playwright", "test"])

    def test_repeated_spec_options_preserve_order_and_deduplicate(self):
        validate = runner._validate_specs
        with mock.patch.object(runner, "_validate_specs", side_effect=lambda values: validate(values, self.root)):
            arguments = runner._parse_arguments([
                "--spec", "frontend/e2e/invoice-list.spec.js",
                "--spec", "frontend/e2e/clients.spec.js",
                "--spec", "frontend/e2e/invoice-list.spec.js",
                "--timeout-ms", "60000",
            ])
        self.assertEqual(arguments.spec, [self.first, self.second])
        self.assertEqual(arguments.timeout_ms, 60_000)

    def test_invalid_paths_flags_traversal_and_remote_are_rejected(self):
        for value in [
            "--headed", "--config=evil.js", "https://example.com/a.spec.js",
            "/frontend/e2e/invoice-list.spec.js", "C:/frontend/e2e/invoice-list.spec.js",
            "frontend/e2e/../invoice-list.spec.js", "frontend/../e2e/invoice-list.spec.js",
            "frontend/e2e/nested/invoice-list.spec.js", "frontend\\e2e\\invoice-list.spec.js",
            "frontend/e2e/missing.spec.js", "frontend/e2e/auth.setup.js",
            "frontend/e2e/invoice-list.spec.js --headed", "frontend/e2e/.*.spec.js",
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                runner._validate_specs([value], self.root)

    def test_directory_named_as_spec_is_rejected(self):
        (self.directory / "directory.spec.js").mkdir()
        with self.assertRaises(ValueError):
            runner._validate_specs(["frontend/e2e/directory.spec.js"], self.root)

    def test_symlinks_are_rejected(self):
        with mock.patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaises(ValueError):
                runner._validate_specs(["frontend/e2e/invoice-list.spec.js"], self.root)

    def test_exact_file_filters_escape_regex_and_support_os_separators(self):
        command = runner._playwright_command("npx.cmd", [self.first], 30_000)
        self.assertEqual(command[:4], ["npx.cmd", "playwright", "test", "--timeout=30000"])
        pattern = command[4]
        self.assertIsNotNone(re.search(pattern, self.first.as_posix()))
        self.assertIsNotNone(re.search(pattern, self.first.as_posix().replace("/", "\\")))
        self.assertIsNone(re.search(pattern, self.first.as_posix() + ".other"))
        self.assertIsNone(re.search(pattern, self.first.as_posix().replace(".spec", "Xspec")))

    def test_timeout_range_and_invalid_options_fail_before_launch(self):
        for arguments in [
            ["--timeout-ms", "29999"], ["--timeout-ms", "120001"],
            ["--timeout-ms", "nan"], ["--time", "60000"], ["--headed"], ["--spec", "--headed"],
            ["--spec", "frontend/e2e/missing.spec.js"],
        ]:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with mock.patch.object(runner.subprocess, "run") as run:
                    with mock.patch.object(runner, "_require_available_port") as port:
                        with self.assertRaises(SystemExit) as result:
                            runner.main(arguments)
                        self.assertEqual(result.exception.code, 2)
                        run.assert_not_called()
                        port.assert_not_called()
        for timeout in ("30000", "120000"):
            self.assertEqual(runner._parse_arguments(["--timeout-ms", timeout]).timeout_ms, int(timeout))


if __name__ == "__main__":
    unittest.main()
