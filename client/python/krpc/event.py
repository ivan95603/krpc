from krpc.stream import Stream


class Event(object):
    """ An event. """
    def __init__(self, conn, event):
        self._stream = Stream.from_stream_id(
            conn, event.stream.id, conn._types.bool_type, False)
        self._acquired = False

    def acquire(self):
        """ Acquire the event """
        self._acquired = True
        self.stream.condition.acquire()

    def release(self):
        """ Release the event """
        self.stream.condition.release()
        self._acquired = False

    def wait(self):
        """ Wait until the event is triggered.
            If the event has not been acquired, it will be
            automatically acquired and then released """
        acquired = False
        if not self._acquired:
            acquired = True
            self.acquire()
        self.stream.condition.wait()
        if acquired:
            self.release()

    @property
    def stream(self):
        """ The underlying stream for the event """
        return self._stream
