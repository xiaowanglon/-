#

#

import abc
import os
import re
from pathlib import Path
from exceptions import ProjectNotFound
from exceptions import InvalidTarget


def find_files(dir, patterns):
    """Find files by using glob.

    Patterns should be a list or tuple.
    """
    files = []
    for ptr in patterns:
        files.extend(dir.glob(ptr))

    return files

class ProjectBase(object):
    """
    Abstract class representing a basic project.

    This class defines common interfaces and attributes for a Project object.
    To add new toolchain and it's project class, you should inherit from this
    base.
    """
    __metaclass__ = abc.ABCMeta

    # project extension
    PRJ_GLOB_PATTERN = None

    # NXP MCU SDK MANIFEST object
    SDK_MANIFEST = None

    SDK_ROOT = None

    @classmethod
    def get_ptrs(cls):
        if not cls.PRJ_GLOB_PATTERN:
            raise ValueError("%s.PRJ_GLOB_PATTERN is not defined! Please report bug!" % cls)

        patterns = cls.PRJ_GLOB_PATTERN
        if not isinstance(cls.PRJ_GLOB_PATTERN, (list, tuple)):
            patterns = [patterns]

        return patterns

    @classmethod
    def _get_instance(cls, filepath):
        """From file path."""
        if any([filepath.match(pattern) for pattern in cls.get_ptrs()]):
            prj_obj = cls(str(filepath))
            prj_obj.boardname = re.findall(f"\w+/boards/(\w+)", prj_obj.prjpath.replace("\\", "/"))[-1]
            return prj_obj
        return

    @classmethod
    def fromdir(cls, path):
        """Find projects from directory or file.

        Arguments:
            path: {str} directory.

        Returns:
            [Project]: a list of projects.
        """
        prjs = list()
        search_path = Path(path)

        if search_path.is_file():
            try:
                ins = cls._get_instance(search_path)
                if ins:
                    prjs.append(ins)
            except ProjectNotFound:
                pass

        else:
            for filepath in find_files(search_path, cls.get_ptrs()):
                try:
                    ins = cls._get_instance(filepath)
                    if ins:
                        prjs.append(ins)
                except:
                    pass

        return prjs

    @classmethod
    def frompath(cls, path):
        """Find one project instance from a given file path or directory.

        WARNING: deprecated function. please use .fromdir()

        Arguments:
            path: {str} file path or directory.

        Returns:
            Project or None
        """
        prjs = cls.fromdir(path)
        if prjs:
            return prjs[0]
        return

    def __init__(self, path, *args, **kwargs):
        """Defaqult Constructor"""
        self.prjpath = path
        self.prjdir = os.path.dirname(path)

        # empty string means current directory
        if self.prjdir == "":
            self.prjdir = "."

        self._conf = None
        self._targets = list()
        self.sdk_root = None
        self.boardname = None

    @property
    def targets(self):
        """Get targets"""
        return list(self._targets)

    @property
    def targetsinfo(self):
        """Returns a dict about the targets data.

        Example:
        {
            "Debug":   "debug_output_dir/output_name",
            "Release": "release_output_dir/output_name",
        }
        """
        return self._conf

    @abc.abstractproperty
    def name(self):
        """Get project name"""
        return

    def map_target(self, input_target):
        """Try to return correct target value by using string to match.

        If not found InvalidTarget exception will be raised.
        """
        input_target = input_target.strip()
        # map for mdk
        for tname in self.targets:
            if input_target == tname or input_target in tname.split():
                return tname

        # map for general
        for tname in self.targets:
            if input_target.lower() in tname.lower():
                return tname

        for tname in self.targets:
            print("!@ avaliable target: %s" % tname)

        msg = "Cannot map the input target: {}, project: {}, valid targets: {}"\
            .format(input_target, self.prjpath, str(self.targets))
        raise InvalidTarget(msg)

    @property
    def idename(self):
        """Name of toolchain/ide"""
        return str(self.__module__).split('.')[-2]

    def to_dict(self):
        """Dump project basic info to a dict.

        Sample:
            {
                'toolchain': "iar",
                'targets': ["debug", "release"],
                'project': "C:/path/project/",
                'name': "hello_world_project"
            }
        """
        return {
            'toolchain': self.idename,
            'targets': self.targets,
            'project': self.prjpath,
            'name': self.name
        }
