import unittest
import joerd.download as download
try:
    # Python 2.x
    import BaseHTTPServer as http
except ImportError:
    # Python 3.x
    from http import server as http
import contextlib
from httptestserver import Server
import re
import sys


# simple handler which does what most HTTP servers (should) do; responds with
# the whole requested file.
class _SimpleHandler(http.BaseHTTPRequestHandler):
    def __init__(self, value, *args):
        self.value = value
        http.BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', len(self.value))
        self.end_headers()
        self.wfile.write(self.value)


# handler which emulates the GMTED server / TCP-layer rate-limiter; it drops
# connections after some number of bytes.
class _DroppingHandler(http.BaseHTTPRequestHandler):
    def __init__(self, value, max_len_obj, support_range, *args):
        self.value = value
        self.max_len_obj = max_len_obj
        self.support_range = support_range
        http.BaseHTTPRequestHandler.__init__(self, *args)

    def _parse_range(self, r, max_len):
        if r is None:
            return None

        m = re.match('bytes=([0-9]+)-([0-9]*)', r)
        if not m:
            return None

        start = int(m.group(1))
        end = int(m.group(2)) if len(m.group(2)) > 0 else None

        if end is None:
            end = min(start + max_len, len(self.value))
        else:
            end = min(end, start + max_len, len(self.value))

        return (start, end)

    def do_GET(self):
        max_len = self.max_len_obj.get()
        byte_range = self._parse_range(self.headers.get('Range'), max_len)

        if byte_range is None or not self.support_range:
            self.send_response(200)
            if self.support_range:
                self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', len(self.value))
            self.end_headers()
            self.wfile.write(self.value[0:max_len])

        elif byte_range[0] >= len(self.value):
            self.send_response(416)
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()

        else:
            cr = 'bytes %d-%d/%d' % \
                 (byte_range[0], len(self.value) - 1, len(self.value))
            self.send_response(206)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', len(self.value) - byte_range[0])
            self.send_header('Content-Range', cr)
            self.end_headers()
            self.wfile.write(self.value[byte_range[0]:byte_range[1]+1])


class _MaxLenFunc:
    def __init__(self, init_len, incr_len):
        self.length = init_len
        self.incr = incr_len

    def get(self):
        l = self.length
        self.length = l + self.incr
        return l


# guard function to run a test HTTP server on another thread and reap it when
# it goes out of scope.
@contextlib.contextmanager
def _test_http_server(handler):
    server = Server('127.0.0.1', 0, 'http', handler)
    server.start()
    yield server


class TestDownload(unittest.TestCase):

    def test_download_simple(self):
        # Test that the download function can download a file over HTTP.
        value = "Some random string here."

        def _handler(*args):
            return _SimpleHandler(value, *args)

        def _verifier(filelike):
            return filelike.read() == value

        with _test_http_server(_handler) as server:
            with download.get(server.url('/'), dict(
                    verifier=_verifier, tries=1)) as data:
                self.assertEqual(value, data.read())

    def test_download_restart(self):
        # Test that the download function can handle restarting, and fetching
        # a file as a series of smaller byte ranges.
        value = "Some random string here."

        # The server will only return 4-byte chunks, but it should be possible
        # to download the whole file eventually.
        max_len = _MaxLenFunc(4, 0)

        def _handler(*args):
            return _DroppingHandler(value, max_len, True, *args)

        def _verifier(filelike):
            v = filelike.read() == value
            return v

        with _test_http_server(_handler) as server:
            with download.get(server.url('/'), dict(
                    verifier=_verifier, tries=(len(value) / 4 + 1))) as data:
                self.assertEqual(value, data.read())

    def test_download_restart_from_scratch(self):
        # Test that the download function can handle restarting from scratch
        # if the server doesn't support byte range requests.
        value = "Some random string here."

        # The server initially doesn't give the whole file, but eventually
        # will.
        max_len = _MaxLenFunc(4, 4)

        def _handler(*args):
            return _DroppingHandler(value, max_len, False, *args)

        def _verifier(filelike):
            v = filelike.read() == value
            return v

        with _test_http_server(_handler) as server:
            with download.get(server.url('/'), dict(
                    verifier=_verifier, tries=(len(value) / 4 + 1))) as data:
                self.assertEqual(value, data.read())
