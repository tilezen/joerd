from contextlib import contextmanager, closing
import urllib2
import tempfile
import os
import logging
import shutil


# Custom error wrapper for (known) exceptions thrown by the download module.
class DownloadFailedError(Exception):
    pass


@contextmanager
def get(url, options={}):
    """
    Download a file to a temporary directory, returning it.

    The options provided will control the behaviour of the download algorithm.

      * 'tries' - The maximum number of tries to download the file before
        giving up and raising an exception.
      * 'timeout' - Timeout in seconds before considering the connection to
        have failed.
      * 'verifier' - A function which is called with a filelike object. It
        should return True if the file is okay and appears to be fully
        downloaded.
    """
    with closing(tempfile.NamedTemporaryFile()) as tmp:
        # current file position = number of bytes read
        filepos = 0

        # file size when downloaded, if known
        filesize = None

        # number of attempts so far
        tries = 0

        # maximum number of attempts to make
        max_tries = options.get('tries', 1)

        # timeout for blocking operations (e.g: connect) in seconds
        timeout = options.get('timeout', 60)

        # verifier function
        verifier = options.get('verifier')

        # whether the server supports Range headers (if it doesn't we'll have
        # to restart from the beginning every time).
        accept_range = False

        # we need to download _something_ if the file position is less than the
        # known size, or the size is unknown.
        while filesize is None or filepos < filesize:
            # explode if we've exceeded the number of allowed attempts
            if tries >= max_tries:
                raise DownloadFailedError("Max tries exceeded (%d) while "
                                          "downloading file %r"
                                          % (max_tries, url))
            else:
                tries += 1

            req = urllib2.Request(url)

            # if the server supports accept range, and we have a partial
            # download then attemp to resume it.
            if accept_range and filepos > 0:
                assert filesize is not None
                req.headers['Range'] = 'bytes=%s-%s' % (filepos, filesize - 1)
            else:
                # otherwise, truncate the file in readiness to download from
                # scratch.
                filepos = 0
                tmp.seek(0, os.SEEK_SET)
                tmp.truncate(0)

            f = urllib2.urlopen(req, timeout=timeout)

            # try to get the filesize, if the server reports it.
            if filesize is None:
                filesize = int(f.info().get('Content-Length'))

            # detect whether the server accepts Range requests.
            accept_range = f.info().get('Accept-Ranges') == 'bytes'

            # copy data from the server
            shutil.copyfileobj(f, tmp)

            # update number of bytes read (this would be nicer if copyfileobj
            # returned it.
            filepos = tmp.tell()

            # if we don't know how large the file is supposed to be, then
            # verify it every time.
            if filesize is None and verifier is not None:
                # reset tmp file to beginning for verification
                tmp.seek(0, os.SEEK_SET)
                if verifier(tmp):
                    break
                # no need to reset here - since filesize is none, then we'll be
                # downloading from scratch, which will truncate the file.

        # verify the file, if it hasn't been verified before
        if filesize is not None and verifier is not None:
            # reset tmp file to beginning for verification
            tmp.seek(0, os.SEEK_SET)
            if not verifier(tmp):
                raise DownloadFailedError("File downloaded from %r failed "
                                          "verification" % url)

        tmp.seek(0, os.SEEK_SET)
        yield tmp
