import tempfile
import shutil
from contextlib2 import contextmanager


# Equivalent of NamedTemporaryFile, but for directories. Will completely
# remove the directory on exit.
@contextmanager
def tmpdir():
    path = tempfile.mkdtemp()

    try:
        yield path

    finally:
        shutil.rmtree(path, ignore_errors=True)
