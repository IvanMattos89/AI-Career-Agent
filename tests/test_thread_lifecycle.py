import unittest

from app.ui.workers import shutdown_threads


class FakeThread:
    def __init__(self, running=True, waits=(True,)):
        self.running = running
        self.waits = iter(waits)
        self.interruptions = 0
        self.quits = 0
        self.terminations = 0

    def isRunning(self):
        return self.running

    def requestInterruption(self):
        self.interruptions += 1

    def quit(self):
        self.quits += 1

    def wait(self, *_args):
        return next(self.waits, True)

    def terminate(self):
        self.terminations += 1


class ThreadLifecycleTest(unittest.TestCase):
    def test_requests_cooperative_shutdown_and_waits(self):
        thread = FakeThread()

        shutdown_threads((None, thread))

        self.assertEqual(thread.interruptions, 1)
        self.assertEqual(thread.quits, 1)
        self.assertEqual(thread.terminations, 0)

    def test_waits_safely_when_a_thread_misses_the_deadline(self):
        thread = FakeThread(waits=(False, True))

        shutdown_threads((thread,), timeout_ms=1)

        self.assertEqual(thread.terminations, 0)

    def test_ignores_finished_threads(self):
        thread = FakeThread(running=False)

        shutdown_threads((thread,))

        self.assertEqual(thread.interruptions, 0)


if __name__ == "__main__":
    unittest.main()
