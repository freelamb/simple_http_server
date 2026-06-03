#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Simple HTTP Server With Upload.
This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.
"""

__version__ = "0.3.6"
__author__ = "yangyongbao@126.com"
__all__ = ["SimpleHTTPRequestHandler"]

import os
import sys
import argparse
import posixpath
try:
    from html import escape
except ImportError:
    from cgi import escape
import shutil
import mimetypes
import re
import signal
import socket
from io import BytesIO

if sys.version_info.major == 3:
    # Python3
    from importlib import reload
    from urllib.parse import quote
    from urllib.parse import unquote
    from http.server import ThreadingHTTPServer
    from http.server import BaseHTTPRequestHandler
else:
    # Python2
    reload(sys)
    sys.setdefaultencoding('utf-8')
    from urllib import quote
    from urllib import unquote
    from BaseHTTPServer import HTTPServer as BaseHTTPServer
    from BaseHTTPServer import BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn

    class ThreadingHTTPServer(ThreadingMixIn, BaseHTTPServer):
        daemon_threads = True


BYTES_PER_MIB = 1024 * 1024
DEFAULT_MAX_UPLOAD_SIZE_MIB = None
MAX_UPLOAD_SIZE = None

try:
    CONNECTION_ERRORS = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)
except NameError:
    CONNECTION_ERRORS = (socket.error,)


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET/HEAD/POST commands.
    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can receive file uploaded
    by client.
    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.
    """

    server_version = "simple_http_server/" + __version__
    max_upload_size = MAX_UPLOAD_SIZE

    def handle(self):
        try:
            BaseHTTPRequestHandler.handle(self)
        except CONNECTION_ERRORS:
            self.close_connection = True

    def do_GET(self):
        """Serve a GET request."""
        fd = self.send_head()
        if fd:
            shutil.copyfileobj(fd, self.wfile)
            fd.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        fd = self.send_head()
        if fd:
            fd.close()

    def do_POST(self):
        """Serve a POST request."""
        if self.is_upload_too_large():
            self.close_connection = True
            self.send_error(
                413,
                "Upload exceeds the %d MiB limit" % (self.max_upload_size // BYTES_PER_MIB),
            )
            return
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(html_escape(info).encode('utf-8'))
        f.write(b"<br><a href=\".\">back</a>")
        f.write(b"<hr><small>Powered By: freelamb, check new version at ")
        f.write(b"<a href=\"https://github.com/freelamb/simple_http_server\">")
        f.write(b"here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()

    def is_upload_too_large(self):
        if self.max_upload_size is None:
            return False
        content_length = self.headers.get('content-length')
        if not content_length:
            return False
        try:
            return int(content_length) > self.max_upload_size
        except ValueError:
            return False

    def deal_post_data(self):
        content_type = self.headers.get("Content-Type", "")
        match = re.search(r'boundary=([^;]+)', content_type)
        if not match or "multipart/form-data" not in content_type.lower():
            return False, "Content-Type must be multipart/form-data"
        boundary = match.group(1).strip().strip('"').encode('utf-8')
        if not boundary:
            return False, "Upload boundary is empty"
        content_length = self.headers.get('content-length')
        if not content_length:
            return False, "Missing content-length header"
        try:
            remain_bytes = int(content_length)
        except ValueError:
            return False, "Invalid content-length header"
        if remain_bytes < 0:
            return False, "Invalid content-length header"
        if self.max_upload_size is not None and remain_bytes > self.max_upload_size:
            return False, "Upload exceeds the %d byte limit" % self.max_upload_size

        remain_bytes_value = [remain_bytes]

        def read_upload_line():
            line = self.rfile.readline()
            remain_bytes_value[0] -= len(line)
            return line, len(line)

        def boundary_state(line):
            stripped = line.rstrip(b'\r\n')
            delimiter = b'--' + boundary
            if stripped == delimiter:
                return "next"
            if stripped == delimiter + b'--':
                return "close"
            return None

        def read_part_headers():
            headers = []
            while True:
                line, line_length = read_upload_line()
                if not line:
                    return None, line_length, "Unexpected end of multipart headers"
                if line in (b'\r\n', b'\n'):
                    return headers, line_length, None
                headers.append(line.decode('utf-8', 'replace'))

        def unique_upload_path(directory, filename):
            target = os.path.join(directory, filename)
            while os.path.exists(target):
                target += "_"
            return target

        def remove_files(paths):
            for file_path in paths:
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        def write_file_content(out):
            pre_line = None
            while True:
                line, line_length = read_upload_line()
                if not line:
                    return None, line_length, "Unexpected end of data."
                state = boundary_state(line)
                if state:
                    if pre_line is not None:
                        pre_line = pre_line[0:-1]
                        if pre_line.endswith(b'\r'):
                            pre_line = pre_line[0:-1]
                        out.write(pre_line)
                    return state, line_length, None
                if pre_line is not None:
                    out.write(pre_line)
                pre_line = line

        line, _ = read_upload_line()
        if not line or boundary_state(line) != "next":
            return False, "Content NOT begin with boundary"

        path = translate_path(self.path)
        if not os.path.isdir(path):
            return False, "Upload target is not a directory"

        uploaded_files = []
        while remain_bytes_value[0] > 0:
            part_headers, _, error = read_part_headers()
            if error:
                remove_files(uploaded_files)
                return False, error

            header_text = "".join(part_headers)
            fn = re.findall(r'Content-Disposition.*name="file"; filename="([^"]*)"', header_text)
            if not fn:
                remove_files(uploaded_files)
                return False, "Can't find out file name..."
            if fn[0] == "":
                state, _, error = write_file_content(BytesIO())
                if error:
                    remove_files(uploaded_files)
                    return False, error
                if state == "close":
                    break
                continue
            fn = sanitize_upload_filename(fn[0])
            if not fn:
                remove_files(uploaded_files)
                return False, "Unsafe upload file name"

            target_path = unique_upload_path(path, fn)
            try:
                out = open(target_path, 'wb')
            except IOError:
                remove_files(uploaded_files)
                return False, "Can't create file to write, do you have permission to write?"

            success = False
            try:
                state, _, error = write_file_content(out)
                if error:
                    return False, error
                success = True
            finally:
                out.close()
                if not success:
                    remove_files(uploaded_files + [target_path])
            if not success:
                return False, "Unexpected end of data."
            uploaded_files.append(target_path)
            if state == "close":
                break

        if not uploaded_files:
            return False, "No files uploaded"
        if len(uploaded_files) == 1:
            return True, "File '%s' upload success!" % os.path.basename(uploaded_files[0])
        return True, "%d files upload success!" % len(uploaded_files)

    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the output file by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", content_type)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_dir = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list_dir.sort(key=lambda a: a.lower())
        f = BytesIO()
        display_path = html_escape(unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Directory listing for %s</title>\n" % display_path.encode('utf-8'))
        f.write(b"<body>\n<h2>Directory listing for %s</h2>\n" % display_path.encode('utf-8'))
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\" multiple/>")
        f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n<ul>\n")
        for name in list_dir:
            fullname = os.path.join(path, name)
            display_name = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                display_name = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                display_name = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write(b'<li><a href="%s">%s</a>\n' % (quote(linkname).encode('utf-8'), html_escape(display_name).encode('utf-8')))
        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def guess_type(self, path):
        """Guess the type of a file.
        Argument is a PATH (a filename).
        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.
        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.
        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })


def html_escape(value):
    """Escape user-controlled text for safe HTML output."""
    return escape(value, quote=True)


def sanitize_upload_filename(filename):
    """Return a safe upload filename, or None when the name is unsafe."""
    filename = filename.replace('\x00', '').strip()
    normalized = filename.replace('\\', '/')
    drive, filename_without_drive = os.path.splitdrive(filename)
    if drive or filename_without_drive != filename:
        return None
    if re.match(r'^[A-Za-z]:', filename):
        return None
    if '/' in normalized:
        return None
    if filename in ('', os.curdir, os.pardir):
        return None
    return filename


def translate_path(path):
    """Translate a /-separated PATH to the local filename syntax.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]
    path = posixpath.normpath(unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = os.getcwd()
    for word in words:
        drive, word = os.path.splitdrive(word)
        head, word = os.path.split(word)
        if word in (os.curdir, os.pardir):
            continue
        path = os.path.join(path, word)
    return path


def signal_handler(signal, frame):
    print("You choose to stop me.")
    exit()

def positive_int(value):
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("%s is not an integer" % value)
    if result <= 0:
        raise argparse.ArgumentTypeError("%s is not a positive integer" % value)
    return result

def _argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', metavar='ADDRESS', default='127.0.0.1', help='Specify alternate bind address [default: 127.0.0.1]')
    parser.add_argument('--max-upload-size', metavar='MIB', default=DEFAULT_MAX_UPLOAD_SIZE_MIB, type=positive_int, help='Maximum upload request size in MiB [default: unlimited]')
    parser.add_argument('--version', '-v', action='version', version=__version__)
    parser.add_argument('port', action='store', default=8000, type=int, nargs='?', help='Specify alternate port [default: 8000]')
    return parser.parse_args()

def main():
    args = _argparse()
    # print(args)
    server_address = (args.bind, args.port)
    if args.max_upload_size is None:
        SimpleHTTPRequestHandler.max_upload_size = None
    else:
        SimpleHTTPRequestHandler.max_upload_size = args.max_upload_size * BYTES_PER_MIB
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    httpd = ThreadingHTTPServer(server_address, SimpleHTTPRequestHandler)
    server = httpd.socket.getsockname()
    print("server_version: " + SimpleHTTPRequestHandler.server_version + ", python_version: " + SimpleHTTPRequestHandler.sys_version)
    print("sys encoding: " + sys.getdefaultencoding())
    print("Serving http on: " + str(server[0]) + ", port: " + str(server[1]) + " ... (http://" + server[0] + ":" + str(server[1]) + "/)")
    httpd.serve_forever()

if __name__ == '__main__':
    main()
