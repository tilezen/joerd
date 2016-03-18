import boto3
import json


class Message(object):
    """
    A wrapper around the SQS message, basically to unpack the JSON body and
    hold a message handle so that delete can be called on success.
    """

    def __init__(msg):
        self.msg = msg
        self.body = json.loads(self.msg.body)

    def delete(self):
        self.msg.delete()


class Queue(object):
    """
    A queue which uses SQS behind the scenes to send and receive messages.

    This encodes each job as a JSON payload in the native SQS message type.
    """

    def __init__(config):
        queue_name = config.get('queue_name')
        assert queue_name is not None, \
            "Could not find SQS queue name in config, but this must be " \
            "configured when using SQS queues."

        self.sqs = boto3.resource('sqs')
        self.queue = self.sqs.get_queue_by_name(QueueName=queue_name)
        self.idx = 0

    def batch_size(self):
        return 10

    def send_messages(self, batch):
        entries = []
        for job in batch:
            entries.append(dict(Id=str(self.idx),
                                MessageBody=json.dumps(job)))
            self.idx += 1

        result = self.queue.send_messages(Entries=entries)
        if 'Failed' in result and result['Failed']:
            raise Exception("Failed to enqueue: %r" % result['Failed'])

    def receive_messages(self):
        for msg in self.queue.receive_messages():
            yield SQSMessage(msg)


def create(j, cfg):
    return Queue(cfg)
