import time
import unittest
from krpc.test.servertestcase import ServerTestCase


class TestEvent(ServerTestCase, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestEvent, cls).setUpClass()

    @staticmethod
    def wait():
        time.sleep(0.01)

    def test_event(self):
        event = self.conn.test_service.on_timer(200)
        event.wait()

    def test_event_loop(self):
        event = self.conn.test_service.on_timer(200, repeats=3)
        event.acquire()
        repeat = 0
        while True:
            event.wait()
            repeat += 1
            if repeat == 3:
                break
        event.release()


if __name__ == '__main__':
    unittest.main()
