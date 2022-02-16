from threading import Timer, Lock
from typing import Callable, Any


class Interval:
    """Class for scheduling an periodically action every period in sec
        action can be a function or a method of an object.
        parameter generator is a function, without parameter that it returns a tuple of parameters for the action
        For example
        class MyClass:
             def my_method(par1, par2)

        def generator():
            return time(), time()

        my_class = MyClass()
        interval = Interval(5, my_class.my_method, generator)

        every 5 seconds the object my_classes wil be executed with parameters returned by generator().
        The parameters are evaluated every time they are used.
    """
    def __init__(self, period: int, action: Callable[[Any], Any], parameters_generator: Callable[[], tuple[Any, ...]], autostart=True):
        self.__lock = Lock()
        self.__timer = None
        self.__action = action
        self.__period = period
        self._stopped = True
        self.__parameters_generator = parameters_generator
        if autostart:
            self.start()

    def start(self, start_called_by_run=False):
        with self.__lock:
            if start_called_by_run or self._stopped:
                self._stopped = False
                self.__timer = Timer(self.__period, self._run)
                self.__timer.daemon = True
                self.__timer.start()

    def _run(self):
        self.start(start_called_by_run=True)
        args = self.__parameters_generator()
        self.__action(*args)

    def stop(self):
        with self.__lock:
            self._stopped = True
            self.__timer.cancel()

    def reset(self):
        """Reset the timer at the specified period"""
        self.stop()
        self.start()