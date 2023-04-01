#

#

"""
IDE base class definition.
"""
import abc
import os
from datetime import datetime, timezone

from base import Base
from compilers.decorators import build
from util import get_max_version


class IDEBase(Base):
    """
    An abstract class representing an ide.
    """
    #abc-abstact base class.Ԫ�����������������ģ���������ࡣ
    __metaclass__ = abc.ABCMeta

    ISIDE = True

    # default mcutool workspace for eclipse project
    DEFAULT_MCUTK_WORKSPACE = os.path.expanduser('~') + '/mcutk_workspace'

    @staticmethod
    def parse_build_result():
        """Parse the build result: warnning? pass? failed?"""
        raise NotImplementedError()

    def __init__(self, *args, **kwargs):
        name = str(self.__module__).split('.')[-2]
        super(IDEBase, self).__init__(name, *args, **kwargs)

    @build
    def build_project(self, project, target, logfile, **kwargs):
        """Return a string about the build command line."""

        return self.get_build_command_line(project, target, logfile, **kwargs)

    @abc.abstractmethod
    def get_build_command_line(self, project, target, logfile, **kwargs):
        """Return a string about the build command line."""
        pass

    def __str__(self):
        return self.name + "-" + self.version

    @classmethod
    def discover_installed(cls):
        pass

    @classmethod
    def get_latest(cls):
        """Search and return a latest tool instance in system

        Returns:
            Compiler object
        """
        instances = cls.discover_installed()
        if not instances:
            return

        latest = get_max_version(instances)
        return cls(latest[0], version=str(latest[1]))

    def transform_elf(self, type, in_file, out_file):
        """ELF file format converter.
        This is a general method for general ide instance.
        It will calle bin/arm-none-eabi-objcopy to do the converter.

        Supported types: bin, ihex, srec.

        Arguments:
            type {str} -- which type you want to convert.
            in_file {str} -- path to elf file.
            out_file {str} -- output file

        Raises:
            ReadElfError -- Unknown elf format will raise such error
            Exception -- Convert failed will raise exception

        Returns:
            bool
        """
        raise NotImplementedError("not implemented")

    def get_modify_date(self):
        """Return a datetime object for tool path modification time.

        Returns:
            datetime.datetime
        """
        if not os.path.exists(self.path):
            return None

        return datetime.fromtimestamp(os.stat(self.path).st_mtime, tz=timezone.utc)

    def to_dict(self):
        """A shortcut method to convert object to a dict

        """
        return {
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "modify_date": str(self.get_modify_date())
        }
