import boto3
import json


class Message(object):
    """
    A wrapper around the SQS message, basically to unpack the JSON body and
    hold a message handle so that delete can be called on success.
    """

    def __init__(self, msg):
        self.msg = msg
        self.body = json.loads(self.msg.body)

    def delete(self):
        self.msg.delete()


class Batch(object):
    """
    A batch accumulating jobs and flushing them to the queue when they have
    reached the maximum serialisation size.
    """

    def __init__(self, queue, max_bytes, max_len):
        self.queue = queue
        self.max_bytes = max_bytes
        self.max_len = max_len
        self.batch_count = 0
        self.batch_size = 2
        self.batch = []

    def append(self, job):
        job_json = json.dumps(job)
        job_len = len(job_json) + 1
        assert job_len + 1 < self.max_bytes, "Cannot send job of size %d, " \
            "as this job alone is larger than the maximum job size." \
            % job_len

        # find out whether, when this job is added to the batch, it will be
        # either too long or too large. if either, then we must flush the
        # current batch to make space for this new job.
        next_batch_too_big = self.batch_size + job_len > self.max_bytes
        next_batch_too_long = self.batch_count + 1 > self.max_len

        if next_batch_too_big or next_batch_too_long:
            self.flush()

        self.batch.append(job_json)
        self.batch_size += job_len
        self.batch_count += 1

    def flush(self):
        if len(self.batch) > 0:
            self.queue.send_message("[" + (",".join(batch)) + "]")
            self.batch = []
            self.batch_size = 2
            self.batch_count = 0


class Queue(object):
    """
    A queue which uses SQS behind the scenes to send and receive messages.

    This encodes each job as a JSON payload in the native SQS message type.
    """

    def __init__(self, config):
        queue_name = config.get('queue_name')
        assert queue_name is not None, \
            "Could not find SQS queue name in config, but this must be " \
            "configured when using SQS queues."

        self.sqs = boto3.resource('sqs')
        self.queue = self.sqs.get_queue_by_name(QueueName=queue_name)
        self.idx = 0
        self.max_batch_bytes = config.get('max_bytes', 256 * 1024)
        self.max_batch_len = config.get('max_batch_len', 10)
        self.entries = []
        self.entries_size = 0

    def start_batch(self, max_batch_len):
        max_batch_len = min(max_batch_len, self.max_batch_len)
        return Batch(self, self.max_batch_bytes, max_batch_len)

    def send_message(self, job_json):
        # the batching in the Batch class deals with merging together jobs
        # into arrays of jobs, but sometimes these arrays will be small and
        # we still want to take advantage of message batching at the API
        # level, so we do this "second level" of batching.

        entries_too_long = len(entries) + 1 > self.max_batch_len
        entries_too_large = len(job_json) + self.entries_size > \
                            self.max_batch_bytes

        if entries_too_large or entries_too_long:
            self.flush()

        self.entries.append(dict(Id=str(self.idx), MessageBody=job_json))
        self.entries_size += len(job_json)
        self.idx += 1

    def flush(self):
        result = self.queue.send_messages(Entries=self.entries)
        if 'Failed' in result and result['Failed']:
            raise Exception("Failed to enqueue: %r" % result['Failed'])

        self.entries = []
        self.entries_size = 0

    def receive_messages(self):
        for msg in self.queue.receive_messages():
            yield Message(msg)


def create(j, cfg):
    return Queue(cfg)
