from contextlib import contextmanager, closing
import urllib2
import tempfile
import os
import logging
import shutil
import httplib
import ftplib
from time import sleep


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
    logger = logging.getLogger('download')

    with closing(tempfile.NamedTemporaryFile()) as tmp:
        # current file position = number of bytes read
        filepos = 0

        # file size when downloaded, if known
        filesize = None

        # number of attempts so far
        tries = 0

        # last try which resulted in some forward progress (i.e: filepos got
        # bigger)
        last_successful_try = 0

        # maximum number of attempts to make
        max_tries = options.get('tries', 1)

        # timeout for blocking operations (e.g: connect) in seconds
        timeout = options.get('timeout', 60)

        # verifier function
        verifier = options.get('verifier')

        # backoff function - to delay between retries
        backoff = options.get('backoff')

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
                if backoff and tries > last_successful_try:
                    backoff(tries - last_successful_try)
                tries += 1

            req = urllib2.Request(url)

            # if the server supports accept range, and we have a partial
            # download then attemp to resume it.
            if accept_range and filepos > 0:
                logger.info("Continuing (try %d/%d) at %d bytes: %r"
                            % (tries, max_tries, filepos, url))
                assert filesize is not None
                req.headers['Range'] = 'bytes=%s-%s' % (filepos, filesize - 1)
            else:
                # otherwise, truncate the file in readiness to download from
                # scratch.
                logger.info("Downloading (try %d/%d) %r"
                            % (tries, max_tries, url))
                filepos = 0
                tmp.seek(0, os.SEEK_SET)
                tmp.truncate(0)

            try:
                f = urllib2.urlopen(req, timeout=timeout)

            except (IOError, httplib.HTTPException) as e:
                logger.debug("Got HTTP error: %s" % str(e))
                continue

            except ftplib.all_errors as e:
                logger.debug("Got FTP error: %s" % str(e))
                continue

            # try to get the filesize, if the server reports it.
            if filesize is None:
                filesize = int(f.info().get('Content-Length'))

            # detect whether the server accepts Range requests.
            accept_range = f.info().get('Accept-Ranges') == 'bytes'

            # copy data from the server
            shutil.copyfileobj(f, tmp)

            # update number of bytes read (this would be nicer if copyfileobj
            # returned it.
            old_filepos = filepos
            filepos = tmp.tell()
            if filepos > old_filepos:
                last_successful_try = tries

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


def _exponential_backoff(try_num):
    """
    Backoff exponentially, with each request backing off 2x from the previous
    attempt. The time limits at 10 minutes maximum back-off. This is generally
    a good default if nothing else is known about the upstream rate-limiter.
    """
    secs = min((1 << try_num) - 1, 600)
    sleep(secs)


def options(in_opts={}):
    """
    Extract a set of options from the input and augment them with some
    defaults.
    """

    out_opts = dict()

    backoff = in_opts.get('backoff', 'exponential')
    if backoff == 'exponential':
        out_opts['backoff'] = _exponential_backoff
    else:
        raise Exception("Configuration backoff=%r not understood."
                            % backoff)

    timeout = in_opts.get('timeout', 60)
    out_opts['timeout'] = int(timeout)

    tries = in_opts.get('tries', 10)
    out_opts['tries'] = int(tries)

    return out_opts
