

from enum import Enum

class Result(Enum):
    PASSED = 0
    Errors = 1
    ERRORS = 1
    Warnings = 2
    WARNINGS = 2
    OtherErrors = 3
    Timeout = 4


class BuildResult(object):
    """The class represent build result object."""

    def __init__(self, result, output):
        self._result = result
        self._output = output

    @property
    def result(self):
        return self._result

    @property
    def output(self):
        return self._output

    @property
    def name(self):
        return self._result.name

    @property
    def value(self):
        return self._result.value

    def set_output(self, v):
        self._output = v

    @classmethod
    def map(cls, result, output=None):
        value = result.lower()
        if value in ("pass", "success", "true", "noerror"):
            ret = Result.PASSED

        elif value in ("warnings", "warning"):
            ret = Result.Warnings

        elif value in ("errors", 'error'):
            ret = Result.Errors

        elif value in ('timeout', ):
            ret = Result.Timeout

        else:
            ret = Result.OtherErrors

        return cls(ret, output)
