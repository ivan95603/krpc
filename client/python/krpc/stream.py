import threading
from krpc.decoder import Decoder
from krpc.error import StreamError
import krpc.schema.KRPC_pb2 as KRPC


class Stream(object):
    """ A streamed request. When invoked, returns the
        most recent value of the request. """

    def __init__(self, conn, stream_id, call, return_type,
                 acquire=False, initial_value=None, callbacks=None):
        self._value = initial_value
        self._conn = conn
        self._call = call
        self._return_type = return_type
        self._callbacks = []
        if callbacks is not None:
            self._callbacks.extend(callbacks)
        # Set up and acquire the update condition variable
        self._condition = threading.Condition()
        self._condition.acquire()
        # Add the stream to the server and the cache
        new_stream = False
        with self._conn._stream_cache_lock:
            self._stream_id = stream_id()
            if self._stream_id not in self._conn._stream_cache:
                new_stream = True
                self._conn._stream_cache[self._stream_id] = self
        # Wait for the first update
        if initial_value is None and new_stream:
            self._condition.wait()
        if not acquire:
            self._condition.release()

    @classmethod
    def from_stream_id(cls, conn, stream_id, return_type,
                       initial_value, callbacks=None):
        return cls(conn, lambda: stream_id, None, return_type,
                   initial_value=initial_value, callbacks=callbacks)

    @classmethod
    def from_call(cls, conn, acquire, callbacks, func, *args, **kwargs):
        # Get the request and return type
        if func == getattr:
            # A property or class property getter
            attr = func(args[0].__class__, args[1])
            call = attr.fget._build_call(args[0])
            return_type = attr.fget._return_type
        elif func == setattr:
            # A property setter
            raise StreamError('Cannot stream a property setter')
        elif hasattr(func, '__self__'):
            # A method
            call = func._build_call(func.__self__, *args, **kwargs)
            return_type = func._return_type
        else:
            # A class method
            call = func._build_call(*args, **kwargs)
            return_type = func._return_type
        # Create the stream
        return cls(conn, lambda: conn.krpc.add_stream(call).id, call,
                   return_type, acquire=acquire, callbacks=callbacks)

    def __call__(self):
        """ Get the most recent value for this stream. """
        if isinstance(self._value, Exception):
            raise self._value  # pylint: disable=raising-bad-type
        return self._value

    def acquire(self):
        """ Acquire a lock on the condition variable for the stream """
        self.condition.acquire()

    def release(self):
        """ Release the lock on the condition variable for the stream """
        self.condition.release()

    def wait(self):
        """ Wait until the next stream update """
        self.condition.wait()

    @property
    def condition(self):
        """ Condition variable that is notified when the stream updates """
        return self._condition

    def add_callback(self, callback):
        """ Add a callback that is invoked whenever the stream is updated """
        # Makes a copy of the callback as they are iterated over
        # by the stream update thread
        callbacks = self._callbacks[:]
        callbacks.append(callback)
        self._callbacks = callbacks

    def remove_callback(self, callback, remove_all=False):
        """ Remove a callback. If the callback was added multiple times,
            only one instance will be removed unless remove_all
            is set to True."""
        # Makes a copy of the callback as they are iterated over
        # by the stream update thread
        if remove_all:
            self._callbacks = [x for x in self._callbacks if x != callback]
        else:
            callbacks = self._callbacks[:]
            callbacks.remove(callback)
            self._callbacks = callbacks

    @property
    def callbacks(self):
        """ The callbacks present in this stream """
        return self._callbacks[:]

    def remove(self):
        """ Remove the stream """
        with self._conn._stream_cache_lock:
            if self._stream_id in self._conn._stream_cache:
                self._conn.krpc.remove_stream(self._stream_id)
                del self._conn._stream_cache[self._stream_id]
                self._value = StreamError('Stream has been removed')

    @property
    def return_type(self):
        """ The return type of this stream """
        return self._return_type

    def update(self, value):
        """ Update the stream's most recent value """
        self._condition.acquire()
        self._value = value
        self._condition.notify_all()
        self._condition.release()
        for fn in self._callbacks:
            fn(value)


def add_stream(conn, func, *args, **kwargs):
    """ Create a stream and return it """
    stream = Stream.from_call(conn, False, None, func, *args, **kwargs)
    return conn._stream_cache[stream._stream_id]


def acquire_stream(conn, func, *args, **kwargs):
    """ Create a stream, acquire a lock on its condition and return it """
    stream = Stream.from_call(conn, True, None, func, *args, **kwargs)
    return conn._stream_cache[stream._stream_id]


def callback_stream(conn, callback, func, *args, **kwargs):
    """ Create a stream, acquire a lock on its condition and return it """
    stream = Stream.from_call(conn, False, [callback], func, *args, **kwargs)
    return conn._stream_cache[stream._stream_id]


def update_thread(client, connection, stop, cache, cache_lock):
    while True:

        # Read the size and position of the update message
        data = b''
        while True:
            try:
                data += connection.partial_receive(1)
                size = Decoder.decode_message_size(data)
                break
            except IndexError:
                pass
            except:  # pylint: disable=bare-except
                # TODO: is there a better way to catch exceptions when the
                #      thread is forcibly stopped (e.g. by CTRL+c)?
                return
            if stop.is_set():
                connection.close()
                return

        # Read and decode the update message
        data = connection.receive(size)
        update = Decoder.decode_message(data, KRPC.StreamUpdate)

        # Add the data to the cache
        with cache_lock:
            for result in update.results:
                if result.id not in cache:
                    continue

                # Check for an error response
                if result.result.HasField('error'):
                    cache[result.id].update(
                        client._build_error(result.result.error))
                    continue

                # Decode the return value and store it in the cache
                typ = cache[result.id].return_type
                value = Decoder.decode(result.result.value, typ)
                cache[result.id].update(value)
