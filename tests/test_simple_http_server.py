import os
from io import BytesIO
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


class DummyUploadHandler(object):
    max_upload_size = simple_http_server.MAX_UPLOAD_SIZE

    def __init__(
        self,
        body,
        content_length=None,
        content_type='multipart/form-data; boundary=test-boundary',
        path='/',
    ):
        self.headers = {
            'Content-Type': content_type,
            'content-length': str(len(body) if content_length is None else content_length),
        }
        self.rfile = BytesIO(body)
        self.path = path

    def deal_post_data(self):
        return simple_http_server.SimpleHTTPRequestHandler.deal_post_data(self)


class UploadParsingTests(unittest.TestCase):
    boundary = b'test-boundary'

    def make_body(self, filename, content, include_content_type=False, close=True):
        headers = [
            b'--' + self.boundary,
            b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"',
        ]
        if include_content_type:
            headers.append(b'Content-Type: application/octet-stream')
        headers.append(b'')
        terminator = b'--' + self.boundary + (b'--' if close else b'')
        return b'\r\n'.join(headers) + b'\r\n' + content + b'\r\n' + terminator + b'\r\n'

    def make_batch_body(self, files):
        body = []
        for filename, content in files:
            body.extend([
                b'--' + self.boundary,
                b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"',
                b'',
                content,
            ])
        body.append(b'--' + self.boundary + b'--')
        return b'\r\n'.join(body) + b'\r\n'

    def run_upload(self, body, content_length=None):
        old_cwd = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        try:
            os.chdir(temp_dir)
            handler = DummyUploadHandler(body, content_length=content_length)
            result = handler.deal_post_data()
            files = {}
            for name in os.listdir(temp_dir):
                with open(os.path.join(temp_dir, name), 'rb') as uploaded:
                    files[name] = uploaded.read()
            return result, files
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(temp_dir)

    def test_upload_without_part_content_type_preserves_file_content(self):
        body = self.make_body(b'example.txt', b'first line\r\nsecond line')

        result, files = self.run_upload(body)

        self.assertTrue(result[0], result[1])
        self.assertEqual(files, {'example.txt': b'first line\r\nsecond line'})

    def test_upload_content_may_contain_boundary_text(self):
        body = self.make_body(
            b'example.txt',
            b'before\r\nnot a delimiter: --test-boundary\r\nafter',
        )

        result, files = self.run_upload(body)

        self.assertTrue(result[0], result[1])
        self.assertEqual(
            files,
            {'example.txt': b'before\r\nnot a delimiter: --test-boundary\r\nafter'},
        )

    def test_interrupted_upload_fails_and_removes_partial_file(self):
        body = b'\r\n'.join([
            b'--' + self.boundary,
            b'Content-Disposition: form-data; name="file"; filename="partial.txt"',
            b'',
            b'partial content without closing boundary',
        ])

        result, files = self.run_upload(body, content_length=len(body) + 20)

        self.assertFalse(result[0])
        self.assertEqual(result[1], 'Unexpected end of data.')
        self.assertEqual(files, {})

    def test_upload_accepts_multiple_files(self):
        body = self.make_batch_body([
            (b'one.txt', b'one'),
            (b'two.txt', b'two'),
        ])

        result, files = self.run_upload(body)

        self.assertTrue(result[0], result[1])
        self.assertEqual(result[1], '2 files upload success!')
        self.assertEqual(files, {'one.txt': b'one', 'two.txt': b'two'})

    def test_upload_keeps_duplicate_batch_names_unique(self):
        body = self.make_batch_body([
            (b'example.txt', b'first'),
            (b'example.txt', b'second'),
        ])

        result, files = self.run_upload(body)

        self.assertTrue(result[0], result[1])
        self.assertEqual(files, {'example.txt': b'first', 'example.txt_': b'second'})

    def test_upload_without_selected_files_fails(self):
        body = self.make_batch_body([
            (b'', b''),
        ])

        result, files = self.run_upload(body)

        self.assertFalse(result[0])
        self.assertEqual(result[1], 'No files uploaded')
        self.assertEqual(files, {})


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
        self.assertIsNone(args.max_upload_size)

    def test_custom_max_upload_size(self):
        old_argv = sys.argv
        sys.argv = ["simple_http_server.py", "--max-upload-size", "1024"]
        try:
            args = simple_http_server._argparse()
        finally:
            sys.argv = old_argv
        self.assertEqual(args.max_upload_size, 1024)

    def test_max_upload_size_must_be_positive(self):
        old_argv = sys.argv
        sys.argv = ["simple_http_server.py", "--max-upload-size", "0"]
        try:
            with self.assertRaises(SystemExit):
                simple_http_server._argparse()
        finally:
            sys.argv = old_argv


class ConnectionHandlingTests(unittest.TestCase):
    def test_client_disconnect_does_not_escape_handler(self):
        handler = simple_http_server.SimpleHTTPRequestHandler.__new__(
            simple_http_server.SimpleHTTPRequestHandler
        )
        handler.close_connection = False

        original_handle = simple_http_server.BaseHTTPRequestHandler.handle

        def raise_disconnect(_self):
            raise simple_http_server.CONNECTION_ERRORS[0]()

        simple_http_server.BaseHTTPRequestHandler.handle = raise_disconnect
        try:
            handler.handle()
        finally:
            simple_http_server.BaseHTTPRequestHandler.handle = original_handle

        self.assertTrue(handler.close_connection)


class UploadLimitTests(unittest.TestCase):
    def test_upload_size_is_unlimited_by_default(self):
        handler = simple_http_server.SimpleHTTPRequestHandler.__new__(
            simple_http_server.SimpleHTTPRequestHandler
        )
        handler.headers = {'content-length': str(1024 * 1024 * 1024 * 10)}
        handler.max_upload_size = None

        self.assertFalse(handler.is_upload_too_large())

    def test_configured_large_upload_is_reported_as_too_large(self):
        handler = simple_http_server.SimpleHTTPRequestHandler.__new__(
            simple_http_server.SimpleHTTPRequestHandler
        )
        handler.headers = {'content-length': str((100 * simple_http_server.BYTES_PER_MIB) + 1)}
        handler.max_upload_size = 100 * simple_http_server.BYTES_PER_MIB

        self.assertTrue(handler.is_upload_too_large())


class PackagingMetadataTests(unittest.TestCase):
    def test_pyproject_exposes_console_script_and_current_version(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "pyproject.toml"), "r", encoding="utf-8") as pyproject:
            metadata = pyproject.read()

        self.assertIn('version = "%s"' % simple_http_server.__version__, metadata)
        self.assertIn('simple-http-server-upload = "simple_http_server:main"', metadata)


if __name__ == "__main__":
    unittest.main()
