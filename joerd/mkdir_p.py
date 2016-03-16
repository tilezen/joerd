import os
import os.path
import errno


def mkdir_p(dirname):
    """
    A function which makes a directory and doesn't throw an exception if it
    already exists.
    """

    if os.path.isdir(dirname):
        return

    try:
        os.makedirs(dirname)
    except OSError as e:
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            raise e
