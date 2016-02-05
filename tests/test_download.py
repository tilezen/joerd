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


class _SimpleHandler(http.BaseHTTPRequestHandler):
    def __init__(self, value, *args):
        self.value = value
        http.BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', len(self.value))
        self.end_headers()
        self.wfile.write(self.value)


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
