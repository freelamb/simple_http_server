import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simple_http_server


class HelperFunctionTests(unittest.TestCase):
    def test_sanitize_upload_filename_accepts_plain_names(self):
        self.assertEqual(
            simple_http_server.sanitize_upload_filename("example.txt"),
            "example.txt",
        )

    def test_sanitize_upload_filename_rejects_paths(self):
        unsafe_names = [
            "../secret.txt",
            "/tmp/secret.txt",
            "nested/secret.txt",
            r"nested\secret.txt",
            r"C:\secret.txt",
            "C:secret.txt",
            ".",
            "..",
            "",
        ]
        for name in unsafe_names:
            self.assertIsNone(simple_http_server.sanitize_upload_filename(name))

    def test_html_escape_escapes_quotes_and_tags(self):
        self.assertEqual(
            simple_http_server.html_escape('<a href="x">'),
            '&lt;a href=&quot;x&quot;&gt;',
        )

    def test_translate_path_stays_under_current_directory(self):
        old_cwd = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        try:
            os.chdir(temp_dir)
            try:
                translated = simple_http_server.translate_path("/../../safe.txt")
            finally:
                os.chdir(old_cwd)
        finally:
            shutil.rmtree(temp_dir)
        self.assertEqual(
            os.path.realpath(translated),
            os.path.realpath(os.path.join(temp_dir, "safe.txt")),
        )


class ArgumentParserTests(unittest.TestCase):
    def test_default_bind_is_localhost(self):
        old_argv = sys.argv
        sys.argv = ["simple_http_server.py"]
        try:
            args = simple_http_server._argparse()
        finally:
            sys.argv = old_argv
        self.assertEqual(args.bind, "127.0.0.1")
        self.assertEqual(args.port, 8000)


if __name__ == "__main__":
    unittest.main()
