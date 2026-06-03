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


class TrackingBytesIO(BytesIO):
    def __init__(self, body):
        BytesIO.__init__(self, body)
        self.readline_sizes = []

    def readline(self, size=-1):
        self.readline_sizes.append(size)
        return BytesIO.readline(self, size)


class DummyUploadHandler(object):
    max_upload_size = simple_http_server.MAX_UPLOAD_SIZE

    def __init__(
        self,
        body,
        content_length=None,
        content_type='multipart/form-data; boundary=test-boundary',
        path='/',
        rfile=None,
    ):
        self.headers = {
            'Content-Type': content_type,
            'content-length': str(len(body) if content_length is None else content_length),
        }
        self.rfile = rfile or BytesIO(body)
        self.path = path

    def deal_post_data(self):
        return simple_http_server.SimpleHTTPRequestHandler.deal_post_data(self)


class UploadParsingTests(unittest.TestCase):
    boundary = b'test-boundary'

    def make_body(
        self,
        filename,
        content,
        include_content_type=False,
        close=True,
        boundary=None,
        disposition=None,
    ):
        boundary = boundary or self.boundary
        disposition = disposition or (
            b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"'
        )
        headers = [
            b'--' + boundary,
            disposition,
        ]
        if include_content_type:
            headers.append(b'Content-Type: application/octet-stream')
        headers.append(b'')
        terminator = b'--' + boundary + (b'--' if close else b'')
        return b'\r\n'.join(headers) + b'\r\n' + content + b'\r\n' + terminator + b'\r\n'

    def run_upload(
        self,
        body,
        content_length=None,
        content_type='multipart/form-data; boundary=test-boundary',
        existing_files=None,
        rfile=None,
    ):
        old_cwd = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        try:
            os.chdir(temp_dir)
            for name, content in (existing_files or {}).items():
                with open(name, 'wb') as existing_file:
                    existing_file.write(content)
            handler = DummyUploadHandler(
                body,
                content_length=content_length,
                content_type=content_type,
                rfile=rfile,
            )
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

    def test_quoted_boundary_with_semicolon_uploads_successfully(self):
        boundary = b'test;boundary'
        body = self.make_body(b'quoted.txt', b'content', boundary=boundary)

        result, files = self.run_upload(
            body,
            content_type='multipart/form-data; boundary="test;boundary"',
        )

        self.assertTrue(result[0], result[1])
        self.assertEqual(files, {'quoted.txt': b'content'})

    def test_content_disposition_parameter_order_is_flexible(self):
        body = self.make_body(
            b'ordered.txt',
            b'ordered content',
            disposition=(
                b'Content-Disposition: form-data; filename="ordered.txt"; name="file"'
            ),
        )

        result, files = self.run_upload(body)

        self.assertTrue(result[0], result[1])
        self.assertEqual(files, {'ordered.txt': b'ordered content'})

    def test_readline_calls_are_limited_to_remaining_content_length(self):
        body = self.make_body(b'limited.txt', b'limited content')
        rfile = TrackingBytesIO(body)

        result, files = self.run_upload(body, rfile=rfile)

        self.assertTrue(result[0], result[1])
        self.assertEqual(files, {'limited.txt': b'limited content'})
        self.assertNotIn(-1, rfile.readline_sizes)

    def test_quoted_backslash_filename_is_rejected(self):
        body = self.make_body(b'ignored.txt', b'bad', disposition=(
            b'Content-Disposition: form-data; name="file"; filename="nested\\secret.txt"'
        ))

        result, files = self.run_upload(body)

        self.assertFalse(result[0])
        self.assertEqual(result[1], 'Unsafe upload file name')
        self.assertEqual(files, {})

    def test_duplicate_upload_uses_unique_filename(self):
        body = self.make_body(b'duplicate.txt', b'new content')

        result, files = self.run_upload(
            body,
            existing_files={'duplicate.txt': b'old content'},
        )

        self.assertTrue(result[0], result[1])
        self.assertEqual(
            files,
            {'duplicate.txt': b'old content', 'duplicate.txt_': b'new content'},
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
