#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Simple HTTP Server With Upload.
This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.
"""

__version__ = "0.3.5"
__author__ = "yangyongbao@126.com"
__all__ = ["SimpleHTTPRequestHandler"]

import os
import errno
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


MAX_UPLOAD_SIZE = 100 * 1024 * 1024


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

    def deal_post_data(self):
        content_type = self.headers.get("Content-Type", "")
        content_media_type, content_type_params = parse_header_params(content_type)
        if content_media_type != "multipart/form-data":
            return False, "Content-Type must be multipart/form-data"
        boundary = content_type_params.get("boundary", "").encode('utf-8')
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
        if remain_bytes > self.max_upload_size:
            return False, "Upload exceeds the %d byte limit" % self.max_upload_size

        def is_boundary_line(line):
            stripped = line.rstrip(b'\r\n')
            delimiter = b'--' + boundary
            return stripped == delimiter or stripped == delimiter + b'--'

        line, line_length = read_limited_line(self.rfile, remain_bytes)
        remain_bytes -= line_length
        if not line or not is_boundary_line(line):
            return False, "Content NOT begin with boundary"

        part_headers = []
        while remain_bytes > 0:
            line, line_length = read_limited_line(self.rfile, remain_bytes)
            remain_bytes -= line_length
            if not line:
                return False, "Unexpected end of multipart headers"
            if line in (b'\r\n', b'\n'):
                break
            part_headers.append(line.decode('utf-8', 'replace'))
        else:
            return False, "Unexpected end of multipart headers"

        fn = get_upload_filename(part_headers)
        if not fn:
            return False, "Can't find out file name..."
        fn = sanitize_upload_filename(fn)
        if not fn:
            return False, "Unsafe upload file name"
        path = translate_path(self.path)
        if not os.path.isdir(path):
            return False, "Upload target is not a directory"
        try:
            out, target_path = open_unique_upload_file(path, fn)
        except (IOError, OSError):
            return False, "Can't create file to write, do you have permission to write?"

        success = False
        try:
            pre_line = None
            while remain_bytes > 0:
                line, line_length = read_limited_line(self.rfile, remain_bytes)
                remain_bytes -= line_length
                if not line:
                    return False, "Unexpected end of data."
                if is_boundary_line(line):
                    if pre_line is not None:
                        pre_line = pre_line[0:-1]
                        if pre_line.endswith(b'\r'):
                            pre_line = pre_line[0:-1]
                        out.write(pre_line)
                    success = True
                    return True, "File '%s' upload success!" % os.path.basename(target_path)
                if pre_line is not None:
                    out.write(pre_line)
                pre_line = line
            return False, "Unexpected end of data."
        finally:
            out.close()
            if not success:
                try:
                    os.remove(target_path)
                except OSError:
                    pass

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
        f.write(b"<input name=\"file\" type=\"file\"/>")
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


def read_limited_line(source, remaining_bytes):
    """Read one line without consuming more than the declared body length."""
    if remaining_bytes <= 0:
        return b'', 0
    line = source.readline(remaining_bytes)
    return line, len(line)


def parse_header_params(header_value):
    """Parse a MIME-style header value into a lower-case value and params."""
    parts = []
    current = []
    in_quote = False
    escape_next = False
    for char in header_value:
        if escape_next:
            current.append(char)
            escape_next = False
            continue
        if in_quote and char == '\\':
            current.append(char)
            escape_next = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char == ';' and not in_quote:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    parts.append("".join(current).strip())

    if not parts or not parts[0]:
        return "", {}
    params = {}
    for part in parts[1:]:
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        params[key.strip().lower()] = value.strip()
    return parts[0].lower(), params


def get_upload_filename(part_headers):
    """Extract the upload filename from multipart part headers."""
    for header in part_headers:
        name, separator, value = header.partition(':')
        if not separator or name.strip().lower() != 'content-disposition':
            continue
        disposition, params = parse_header_params(value.strip())
        if disposition == 'form-data' and params.get('name') == 'file':
            return params.get('filename')
    return None


def open_unique_upload_file(directory, filename):
    """Open a unique upload target without racing another writer."""
    target_path = os.path.join(directory, filename)
    while True:
        try:
            fd = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            return os.fdopen(fd, 'wb'), target_path
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise
            target_path += "_"


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

def _argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', metavar='ADDRESS', default='127.0.0.1', help='Specify alternate bind address [default: 127.0.0.1]')
    parser.add_argument('--version', '-v', action='version', version=__version__)
    parser.add_argument('port', action='store', default=8000, type=int, nargs='?', help='Specify alternate port [default: 8000]')
    return parser.parse_args()

def main():
    args = _argparse()
    # print(args)
    server_address = (args.bind, args.port)
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
