

"""
Base class definition.
"""
import abc
import os


class Base(object):
    """
    An abstract class representing the interface for an app.
    """
    __metaclass__ = abc.ABCMeta

    # @staticmethod
    # @abc.abstractmethod
    # def get_latest():
    #     pass

    def __init__(self, name, path="", version=None, **kwargs):
        """Base interface definition.

        Arguments:
            name {string} -- app name
            path {string} -- app path

        Keyword Arguments:
            version {string} -- app version (default: {None})
        """
        self._name = name
        self._path = path
        self.version = version

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if value in (None, "None", ""):
            raise ValueError("invalid name")
        self._name = value

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        if value in (None, "None", ""):
            raise ValueError("invalid path")
        self._path = value

    @abc.abstractproperty
    def is_ready(self):
        return os.path.exists(self._path)

    def show(self):
        attrs = vars(self)
        for attr, value in attrs.items():
            print("{0}: {1}".format(attr, value))

    def __str__(self):
        return f"App({self._name}-{self.version})"
