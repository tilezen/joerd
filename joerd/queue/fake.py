class Queue(object):
    """
    A fake queue, which doesn't store or communicate any messages at all, but
    calls the server to have them processed immediately.

    This is useful for testing and running locally.
    """

    def __init__(self, server):
        self.server = server

    def batch_size(self):
        return 1

    def send_messages(self, batch):
        for msg in batch:
            self.server.dispatch_job(msg)

    def receive_messages(self):
        # fake queue doesn't actually hold any messages, so this is really
        # an error.
        raise Exception("Fake queue doesn't hold any messages.")


def create(j, cfg):
    return Queue(j)
