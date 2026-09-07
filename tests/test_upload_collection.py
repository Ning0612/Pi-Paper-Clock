import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

import upload
from tools.pico_image_tool.conversion import save_bin


class UploadCollectionTests(unittest.TestCase):
    def test_cli_protects_config_by_default_and_requires_opt_in(self):
        self.assertTrue(upload.parse_args([]).no_config)
        self.assertFalse(upload.parse_args(["--include-config"]).no_config)
        self.assertTrue(upload.parse_args(["--no-config"]).no_config)
        self.assertEqual(
            set(upload.PROTECTED_CONFIG_FILES),
            {"config.json", "config.json.tmp", "config.json.bak"},
        )
        self.assertTrue(upload._is_protected_config_path(":config.json"))
        self.assertTrue(upload._is_protected_config_path(":/nested/config.json.bak"))

    def test_cli_finds_unix_mpremote_next_to_python(self):
        original_port = upload.MPREMOTE_PORT
        try:
            upload.MPREMOTE_PORT = "/dev/tty.test"
            with patch.object(upload.shutil, "which", return_value=None), patch.object(
                upload.sys, "executable", "/venv/bin/python"
            ), patch.object(upload.os.path, "exists", side_effect=lambda path: path == "/venv/bin/mpremote"):
                self.assertEqual(
                    upload.get_mpremote_base(),
                    ["/venv/bin/mpremote", "connect", "/dev/tty.test"],
                )
        finally:
            upload.MPREMOTE_PORT = original_port

    def test_serial_deploy_collects_only_ppc1_bin_image(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "src"
            image = source / "image" / "custom" / "sample.bin"
            save_bin(image, b"\x05")
            original_source = upload.SOURCE_DIR
            original_images = upload.UPLOAD_IMAGES
            original_no_config = upload.NO_CONFIG
            try:
                upload.SOURCE_DIR = str(source)
                upload.UPLOAD_IMAGES = True
                upload.NO_CONFIG = False
                relative = {item[1] for item in upload.collect_files()}
            finally:
                upload.SOURCE_DIR = original_source
                upload.UPLOAD_IMAGES = original_images
                upload.NO_CONFIG = original_no_config
            self.assertIn("image/custom/sample.bin", relative)
            self.assertNotIn("image/custom/sample.bin.hlsb", relative)

    def test_specific_cleanup_never_deletes_config_artifacts_by_default(self):
        listing = "\n".join([
            "-rw 1 config.json",
            "-rw 1 config.json.tmp",
            "-rw 1 config.json.bak",
            "-rw 1 nested/config.json",
            "-rw 1 nested/config.json.tmp",
            "-rw 1 nested/config.json.bak",
            "-rw 1 nested/main.py",
        ])
        original_no_config = upload.NO_CONFIG
        commands = []
        try:
            upload.NO_CONFIG = True
            with patch.object(
                upload.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout=listing, stderr=""),
            ), patch.object(
                upload,
                "run_command",
                side_effect=lambda command, **_kwargs: commands.append(command) or True,
            ):
                upload.clean_specific_files()
        finally:
            upload.NO_CONFIG = original_no_config

        removed = [command[-1] for command in commands if command[-2] == "rm"]
        self.assertEqual(removed, [":nested/main.py"])

    def test_specific_cleanup_allows_config_json_only_when_opted_in(self):
        listing = "\n".join([
            "-rw 1 config.json",
            "-rw 1 nested/config.json",
            "-rw 1 nested/main.py",
        ])
        original_no_config = upload.NO_CONFIG
        commands = []
        try:
            upload.NO_CONFIG = False
            with patch.object(
                upload.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout=listing, stderr=""),
            ), patch.object(
                upload,
                "run_command",
                side_effect=lambda command, **_kwargs: commands.append(command) or True,
            ):
                upload.clean_specific_files()
        finally:
            upload.NO_CONFIG = original_no_config

        removed = [command[-1] for command in commands if command[-2] == "rm"]
        self.assertEqual(removed, [":config.json", ":nested/config.json", ":nested/main.py"])

    def test_recursive_cleanup_never_deletes_config_artifacts_by_default(self):
        listings = {
            ":": "\n".join([
                "-rw 1 config.json",
                "-rw 1 config.json.tmp",
                "-rw 1 config.json.bak",
                "d 0 nested/",
            ]),
            ":nested": "\n".join([
                "-rw 1 config.json",
                "-rw 1 config.json.tmp",
                "-rw 1 config.json.bak",
                "-rw 1 main.py",
            ]),
        }
        original_no_config = upload.NO_CONFIG
        original_recursive = upload.ENABLE_RECURSIVE_CLEAN
        commands = []

        def fake_run(command, **_kwargs):
            if command[-2:] == ["fs", "ls"]:
                return SimpleNamespace(returncode=0, stdout=listings[":"], stderr="")
            if command[-3:] == ["fs", "ls", ":"]:
                return SimpleNamespace(returncode=0, stdout=listings[":"], stderr="")
            if command[-3:] == ["fs", "ls", ":nested"]:
                return SimpleNamespace(returncode=0, stdout=listings[":nested"], stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        try:
            upload.NO_CONFIG = True
            upload.ENABLE_RECURSIVE_CLEAN = True
            with patch.object(upload.subprocess, "run", side_effect=fake_run), patch.object(
                upload,
                "run_command",
                side_effect=lambda command, **_kwargs: commands.append(command) or True,
            ):
                upload.clean_all_files()
        finally:
            upload.NO_CONFIG = original_no_config
            upload.ENABLE_RECURSIVE_CLEAN = original_recursive

        removed = [command[-1] for command in commands if command[-2] == "rm"]
        self.assertEqual(removed, [":nested/main.py"])

    def test_recursive_cleanup_allows_config_artifacts_when_opted_in(self):
        listings = {
            ":": "\n".join([
                "-rw 1 config.json",
                "-rw 1 config.json.tmp",
                "-rw 1 config.json.bak",
                "d 0 nested/",
            ]),
            ":nested": "\n".join([
                "-rw 1 config.json",
                "-rw 1 config.json.tmp",
                "-rw 1 config.json.bak",
                "-rw 1 main.py",
            ]),
        }
        original_no_config = upload.NO_CONFIG
        original_recursive = upload.ENABLE_RECURSIVE_CLEAN
        commands = []

        def fake_run(command, **_kwargs):
            if command[-3:] == ["fs", "ls", ":"]:
                return SimpleNamespace(returncode=0, stdout=listings[":"], stderr="")
            if command[-3:] == ["fs", "ls", ":nested"]:
                return SimpleNamespace(returncode=0, stdout=listings[":nested"], stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        try:
            upload.NO_CONFIG = False
            upload.ENABLE_RECURSIVE_CLEAN = True
            with patch.object(upload.subprocess, "run", side_effect=fake_run), patch.object(
                upload,
                "run_command",
                side_effect=lambda command, **_kwargs: commands.append(command) or True,
            ):
                upload.clean_all_files()
        finally:
            upload.NO_CONFIG = original_no_config
            upload.ENABLE_RECURSIVE_CLEAN = original_recursive

        removed = [command[-1] for command in commands if command[-2] == "rm"]
        self.assertEqual(
            removed,
            [
                ":config.json",
                ":config.json.tmp",
                ":config.json.bak",
                ":nested/config.json",
                ":nested/config.json.tmp",
                ":nested/config.json.bak",
                ":nested/main.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
