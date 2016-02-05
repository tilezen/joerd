from contextlib import contextmanager, closing
import requests
import tempfile
import os


@contextmanager
def get(url, options={}):
    with closing(tempfile.NamedTemporaryFile()) as tmp:
        with closing(requests.get(url, stream=True)) as req:
            for chunk in req.iter_content(chunk_size=10240):
                if chunk:
                    tmp.write(chunk)
        tmp.flush()

        tmp.seek(0, os.SEEK_SET)
        yield tmp.file
