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
    def __init__(self, value, max_len, *args):
        self.value = value
        self.max_len = max_len
        http.BaseHTTPRequestHandler.__init__(self, *args)

    def _parse_range(self, r):
        if r is None:
            return None

        m = re.match('bytes=([0-9]+)-([0-9]*)', r)
        if not m:
            return None

        start = int(m.group(1))
        end = int(m.group(2)) if len(m.group(2)) > 0 else None

        if end is None:
            end = min(start + self.max_len, len(self.value))
        else:
            end = min(end, start + self.max_len, len(self.value))

        return (start, end)

    def do_GET(self):
        byte_range = self._parse_range(self.headers.get('Range'))

        if byte_range is None:
            self.send_response(200)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', len(self.value))
            self.end_headers()
            self.wfile.write(self.value[0:self.max_len])

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


# guard function to run a test HTTP server on another thread and reap it when
# it goes out of scope.
@contextlib.contextmanager
def _test_http_server(handler):
    server = Server('127.0.0.1', 0, 'http', handler)
    server.start()
    yield server


class TestDownload(unittest.TestCase):

    def test_download_simple(self):
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
        value = "Some random string here."

        def _handler(*args):
            return _DroppingHandler(value, 4, *args)

        def _verifier(filelike):
            v = filelike.read() == value
            return v

        with _test_http_server(_handler) as server:
            with download.get(server.url('/'), dict(
                    verifier=_verifier, tries=(len(value) / 4 + 1))) as data:
                self.assertEqual(value, data.read())
