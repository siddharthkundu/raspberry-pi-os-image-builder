from __future__ import annotations
from collections.abc import Generator
from typing import TypeVar, Generic, Callable, List

T = TypeVar('T')
U = TypeVar('U')

class Try_(Generic[T]):
    _unhandled = ()

    @staticmethod
    def set_unhandled(es=None):
        """Set a list of the unhandled exceptions.

        :param es: an iterable of exceptions or None

        >>> from operator import getitem
        >>> Try(getitem, [], 0)  # doctest:+ELLIPSIS
        Failure(IndexError(...))
        >>> Try_.set_unhandled([IndexError])
        >>> Try(getitem, [], 0)  # doctest:+ELLIPSIS
        Traceback (most recent call last):
            ...
        IndexError: ...
        >>> Try_.set_unhandled()
        >>> Try(getitem, [], 0)  # doctest:+ELLIPSIS
        Failure(IndexError(...))
        """
        Try_._unhandled = tuple(es) if es is not None else tuple()

    @property
    def _v(self):
        raise NotImplementedError  # pragma: no cover

    @property
    def _fmt(self):
        raise NotImplementedError  # pragma: no cover

    @staticmethod
    def _identity_if_try_or_raise(v, msg="Invalid return type for f: {0}"):
        if not isinstance(v, Try_):
            raise TypeError(msg.format(type(v)))
        return v

    @staticmethod
    def _raise_if_not_exception(e, msg="Invalid type for Failure: {0}"):
        if not isinstance(e, Exception):
            raise TypeError(msg.format(type(e)))

    def __init__(self, _):
        raise NotImplementedError(
            "Use Try function or Success/Failure instead."
        )  # pragma: no cover

    def __ne__(self, other) -> bool:
        """
        >>> Success(1) != Failure(Exception())
        True
        """
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return self._fmt.format(repr(self._v))

    def get(self) -> T:
        """If this is Success get wrapped value otherwise
        throw stored exception

        :return: stored value

        >>> Success(1).get()
        1
        >>> Failure(Exception("e")).get()
        Traceback (most recent call last):
            ...
        Exception: e
        """
        raise NotImplementedError  # pragma: no cover

    def getOrElse(self, default: T) -> T:
        """If this is a Success get stored value otherwise
        return default

        :param default: value to return if this is a Failure
        :return:

        >>> Success(1).getOrElse(0)
        1
        >>> Failure(Exception("e")).getOrElse(0)
        0
        """
        raise NotImplementedError  # pragma: no cover

    def orElse(self, default:T) -> Try_[T]:
        """If this is a Success return self otherwise
        default

        :param default: Try_
        :return:

        >>> Success(1).orElse(Success(0))
        Success(1)
        >>> Failure(Exception("e")).orElse(Success(0))
        Success(0)
        """
        raise NotImplementedError  # pragma: no cover

    def map(self, f: Callable[[T], U]) -> Try_[U]:
        """Apply function to the value.

        :param f: function to be applied
        :return: self if this is a Failure otherwise Try(f, self.get)

        >>> inc = lambda x: x + 1
        >>> def f(e): raise Exception("e")
        >>> Success(1).map(inc)
        Success(2)
        >>> Failure(Exception("e")).map(inc)  # doctest:+ELLIPSIS
        Failure(...)
        >>> Success("1").map(f)  # doctest:+ELLIPSIS
        Failure(...)
        """
        raise NotImplementedError  # pragma: no cover

    def flatMap(self, f: Callable[[T], Try_[U]]) -> Try_[U] :
        """Apply function  returning Try_ to the value.

        :param f: function to be applied.
        :return: self if this is a Failure otherwise f applied to self.get

        >>> from operator import add
        >>> Success(1).flatMap(lambda x: Try(add, x, 1))
        Success(2)
        >>> Failure(Exception("e")).flatMap(lambda x: Try(add, x, 1))  # doctest:+ELLIPSIS
        Failure(...)
        >>> Success(1).flatMap(lambda x: Try(add, x, "0"))  # doctest:+ELLIPSIS
        Failure(TypeError(...))
        """
        raise NotImplementedError  # pragma: no cover

    def filter(self, f: Callable[[T], bool], exception_cls=Exception, msg=None) -> Try_[T]:
        """Convert this to Failure if f(self.get()) evaluates to False

        :param f: function to be applied
        :param exception_cls: optional exception class to return
        :param msg: optional message
        :return: self if f evaluates to True otherwise Failure

        >>> Success(1).filter(lambda x: x > 0)
        Success(1)
        >>> Success(1).filter(lambda x: x < 0, msg="Greater than zero")  # doctest:+ELLIPSIS
        Failure(Exception(...))
        >>> Failure(Exception("e")).filter(lambda x: x)  # doctest:+ELLIPSIS
        Failure(Exception(...))
        """
        raise NotImplementedError  # pragma: no cover

    def recover(self, f: Callable[[T], T]) -> Try_[T]:
        """If this is a Failure apply f to value otherwise

        :param f: function to be applied
        :return: Either Success of Failure

        >>> def f(e): raise Exception("e")
        >>> Success(1).recover(lambda e: 0)
        Success(1)
        >>> Failure(Exception("e")).recover(lambda e: 0)
        Success(0)
        >>> Failure(Exception("e")).recover(f)  # doctest:+ELLIPSIS
        Failure(Exception(...))
        """
        raise NotImplementedError  # pragma: no cover

    def recoverWith(self, f: Callable[[T], Try_[T]]) -> Try_[T]:
        """If this is a Failure apply f to self otherwise
        return this

        :param f: function to be applied
        :return: Either Success of Failure

        >>> Success(1).recoverWith(lambda t: Try(lambda: 0))
        Success(1)
        >>> Failure(Exception("e")).recoverWith(lambda t: Try(lambda: 0))
        Success(0)
        """
        raise NotImplementedError  # pragma: no cover

    def failed(self) -> Try_[T]:
        """Inverts this Try_.

        If it is a Failure it returns its exception wrapped with Success.
        If it is a Success it returns Failure(TypeError())

        :return: Try_[T]

        >>> Success(1).failed()  # doctest:+ELLIPSIS
        Failure(TypeError(...))
        >>> Failure(Exception("e")).failed()  # doctest:+ELLIPSIS
        Success(Exception(...))
        """
        raise NotImplementedError  # pragma: no cover

    @property
    def isFailure(self) -> bool:
        """Check if this is a Failure.

        >>> Success(1).isFailure
        False
        >>> Failure(Exception()).isFailure
        True
        """
        return not bool(self)

    @property
    def isSuccess(self) -> bool:
        """Check if this is a Success.

        >>> Success(1).isSuccess
        True
        >>> Failure(Exception()).isSuccess
        False
        """
        return bool(self)


class Success(Try_[T]):
    """Represents a successful computation"""

    __slots__ = ("_v",)
    _fmt = "Success({0})"

    @staticmethod
    def __len__() -> int:
        return 1

    def __init__(self, v):
        self._v = v

    def __eq__(self, other) -> bool:
        """
        >>> Success(1) == Success(1)
        True
        >>> Success(1) == Success(2)
        False
        >>> Success(1) == 1
        False
        """
        return isinstance(other, Success) and self._v == other._v

    def __hash__(self):
        try:
            return hash(self._v)
        except TypeError as e:
            raise TypeError("Cannot hash try with unhashable value") from e

    def get(self) -> T:
        return self._v

    def getOrElse(self, default: T) -> T:
        return self.get()

    def orElse(self, default:T) -> Try_[T]:
        return self

    def map(self, f: Callable[[T], U]) -> Try_[U]:
        return Try(f, self._v)

    def flatMap(self, f: Callable[[T], Try_[U]]) -> Try_[U] :
        v = Try(f, self._v)
        return Try_._identity_if_try_or_raise(v if v.isFailure else v.get())

    def filter(self, f: Callable[[T], bool], exception_cls=Exception, msg=None) -> Try_[T]:
        if f(self.get()):
            return self
        else:
            return Failure(exception_cls(msg if msg else repr(f)))

    def recover(self, f: Callable[[T], T]) -> Try_[T]:
        return self

    def recoverWith(self, f: Callable[[T], Try_[T]]) -> Try_[T]:
        return self

    def failed(self) -> Try_[T]:
        return Failure(TypeError())


class Failure(Try_[T]):
    """Represents a unsuccessful computation"""

    __slots__ = ("_v",)
    _fmt = "Failure({0})"

    @staticmethod
    def __len__():
        return 0

    def __init__(self, e):
        Try_._raise_if_not_exception(e)
        self._v: Exception = e

    def __eq__(self, other):
        """
        >>> Failure(Exception("e")) == Failure(Exception("e"))
        True
        >>> Failure(Exception(-1)) == Failure(Exception(0))
        False
        >>> Failure(Exception("e")) == Exception("e")
        False
        """
        return (
                isinstance(other, Failure)
                and
                # Want to check an exact type so isinstance or issubclass
                # are not good here
                type(self._v) is type(other._v)
                and self._v.args == other._v.args
        )

    def __hash__(self):
        try:
            return hash(self._v)
        except TypeError as e:
            raise TypeError("Cannot hash try with unhashable value") from e

    def get(self) -> T:
        raise self._v

    def getOrElse(self, default: T) -> T:
        return default

    def orElse(self, default:T) -> Try_[T]:
        return Try_._identity_if_try_or_raise(default)

    def map(self, f: Callable[[T], U]) -> Try_[U]:
        return Failure(self._v)

    def flatMap(self, f: Callable[[T], Try_[U]]) -> Try_[U] :
        return Failure(self._v)

    def filter(self, f: Callable[[T], bool], exception_cls=Exception, msg=None) -> Try_[T]:
        return self

    def recover(self, f: Callable[[T], T]) -> Try_[T]:
        return Success(self._v).map(f)

    def recoverWith(self, f: Callable[[T], Try_[T]]) -> Try_[T]:
        return Success(self._v).flatMap(f)

    def failed(self) -> Try_[T]:
        return Success(self._v)


def Try(f, *args, **kwargs) -> T:
    """Evaluates f with provided arguments and wraps the result
    using either Success or Failure.

    :param f: Either Callable or Iterator or Generator which should be evaluated.
              If f is Callable it is called with given args and kwargs
              If f is Iterator we evaluate its next
              If f is Generator and there is single arg we evaluate f.next(arg)
                In such case f is not primed.

    :param args: args which should be passed to f
    :param kwargs: kwargs which should be passed to f
    :return: Either success or Failure

    >>> from operator import add, truediv
    >>> Try(truediv, 1, 0)  # doctest:+ELLIPSIS
    Failure(ZeroDivisionError(...))
    >>> Try(add, 1, 2)
    Success(3)
    """
    try:
        if callable(f):
            return Success(f(*args, **kwargs))
        elif isinstance(f, Generator) and len(args) == 1 and not kwargs:
            return Success(f.send(args[0]))
        elif isinstance(f, Generator) and not args and not kwargs:
            return Success(next(f))
        else:
            raise TypeError(
                "Don't know how to try {} with {} and {}".format(type(f), args, kwargs)
            )

    except Try_._unhandled as e:  # type: ignore
        raise e
    except Exception as e:
        return Failure(e)


def strip_new_line(input: str) -> str:
    if input == None:
        return None
    result = input
    while len(result) > 0:
        if (result[len(result) - 1] == '\n' or result[len(result) - 1] == '\r'):
            result = result[:-1]
        else:
            break
    return result