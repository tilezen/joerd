class Batch(object):
    """
    A fake batch, which batches nothing and just sends messages on the
    queue immediately.
    """

    def __init__(self, queue, max_batch_len):
        self.queue = queue
        # NOTE: this is ignored, and "batches" always contain a single job.
        self.max_batch_len = max_batch_len

    def append(self, job):
        self.queue.send_message(job)

    def flush(self):
        pass


class Queue(object):
    """
    A fake queue, which doesn't store or communicate any messages at all, but
    calls the server to have them processed immediately.

    This is useful for testing and running locally.
    """

    def __init__(self, server):
        self.server = server

    def start_batch(self, max_batch_len=1):
        return Batch(self, max_batch_len)

    def send_message(self, msg):
        self.server.dispatch_job(msg)

    def flush(self):
        pass

    def receive_messages(self):
        # fake queue doesn't actually hold any messages, so this is really
        # an error.
        raise Exception("Fake queue doesn't hold any messages.")


def create(j, cfg):
    return Queue(j)
