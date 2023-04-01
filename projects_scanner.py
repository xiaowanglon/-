

import os
import logging
import time
from collections import defaultdict
from xml.etree import cElementTree as ET

import click
from globster import Globster

from compilers.projectbase import ProjectBase
from compilers import compilerfactory, SUPPORTED_TOOLCHAINS
from sdk_manifest import SDKManifest
from exceptions import ProjectNotFound, ProjectParserError

LOGGER = logging.getLogger(__name__)



EXCLUDE_DIR_NAME = [
    'log/',
    'debug/',
    'obj/',
    'release/',
    '.debug/',
    '.release/',
    'RTE/',
    'settings/'
    '.git/',
    '__pycache__/',
    'flexspi_nor_debug/',
    'flexspi_nor_release/'
]

IDE_INS = [compilerfactory(toolname) for toolname in SUPPORTED_TOOLCHAINS]
Exclude_Matcher = Globster(EXCLUDE_DIR_NAME)



def identify_project(path, toolname=None, manifest_check=True):
    """ Identify and return initiliazed project instance.

    Arguments:
        path {str} -- project path

    Keyword Arguments:
        toolname {str} -- if toolname is given, it will try to load
            the project with the tool. (default: None)
        manifest_check (bool, optional): Check example is enabled in MCUXpressoIDE manifest. Default True.

    Returns:
        Project object
    """

    if toolname:
        cls = compilerfactory(toolname)
        return cls.Project(path)

    prj = None
    for cls in IDE_INS:
        try:
            prj = cls.Project.frompath(path)
            if not prj:
                continue

            if prj and prj.idename == 'mcux' and manifest_check \
                and not prj.is_enabled:
                logging.debug("not enabled in manifest.")
                return None
            break

        except ProjectParserError as err:
            logging.warning(str(err))
        except ET.ParseError as err:
            logging.error("Bad project: %s, Reason: %s", path, err)
        except ProjectNotFound as err:
            pass

    return prj


def _find_projects(projects, dir):
    for cls in IDE_INS:
        prjs = cls.Project.fromdir(dir)
        if prjs:
            for prj in prjs:
                projects[prj.idename].append(prj)
            break

def find_projects_from_dir(dirs, recursive=False):
    """Find projects from a list of directories.

    Args:
        dirs ([list]): list of directories to search
        recursive (bool, optional): Recursive to search. Defaults to False.

    Returns:
        [type]: [description]
    """
    projects = defaultdict(list)
    for dir in dirs:
        _find_projects(projects, dir)

        if recursive:
            for root, folders, _ in os.walk(dir, topdown=True):
                for folder in folders:
                    if Exclude_Matcher.match(folder):
                        continue

                    path = os.path.join(root, folder)
                    _find_projects(projects, path)

    return projects


def find_projects_from_manifests(sdk_dir, manifests=None):
    """Find projects by searching in SDK manifest."""
    if not manifests:
        if not sdk_dir:
            raise ValueError('invalid sdk_dir')
        manifests = SDKManifest.find(sdk_dir)

    if not manifests:
        return

    projects = defaultdict(list)
    for manifest in manifests:
        examples = manifest.dump_examples()
        search_folders = list()

        # get all examples root dir
        for example in examples:
            example_root = "/".join(example["path"].split("/")[:2])
            if example_root not in search_folders:
                search_folders.append(example_root)

        # get abs search dir
        search_folders = [sdk_dir + "/" + path for path in search_folders]
        ProjectBase.SDK_MANIFEST = manifest
        manifest_prjs = find_projects_from_dir(search_folders, recursive=True)
        if manifest_prjs:
            for key, value in manifest_prjs.items():
                projects[key].extend(value)

    return projects


def find_projects(root_dir, recursive=True, include_tools=None, exclude_tools=None, manifests_dir=None):
    """Find SDK projects/examples in specific directory.

    Arguments:
        root_dir {string} -- root directory
        recursive {bool} -- recursive mode
        include_tools {list} -- only include specifices tools
        exclude_tools {list} -- exlucde specifices tools
    Returns:
        {dict} -- key: toolchain name, value: a list of Project objects.

    Example:
        >> ps = find_projects("C:/code/mcu-sdk-2.0", True)
        >> ps
        {
            'iar': [<Project Object at 0x1123>, <Project Object at 0x1124>],
            'mdk': [<Project Object at 0x1123>, <Project Object at 0x1124>],
            ...
        }
    """
    print('Process scanning')
    sdk_manifest = None
    sdk_root = None
    manifest_list = None
    s_time = time.time()

    # To speed up the performance, use a workaround to find the manifest file.
    if os.path.basename(os.path.abspath(root_dir)) == 'boards':
        sdk_root = os.path.dirname(root_dir)
    else:
        sdk_root = root_dir

    # try to find manifest in current directory
    sdk_manifest = SDKManifest.find_max_version(sdk_root)
    if sdk_manifest:
        LOGGER.debug("Found SDK Manifetst: %s", sdk_manifest)
        ProjectBase.SDK_MANIFEST = sdk_manifest
        ProjectBase.SDK_ROOT = sdk_root.replace('\\', '/') + "/"
    else:
        # search manifest in possible dirs
        if not manifests_dir:
            search_dirs = [
                os.path.join(sdk_root, 'manifests'),
                os.path.join(sdk_root, 'core/manifests'),
                os.path.join(sdk_root, 'examples/manifests')
            ]
        manifest_list = SDKManifest.find(search_dirs)

    # multiple manifests, use manifest to search projects
    if manifest_list:
        print('Multiple manifest files were found in %s' % manifests_dir)
        projects = find_projects_from_manifests(sdk_root, manifests=manifest_list)
    else:
        projects = find_projects_from_dir([root_dir], recursive=recursive)

    if projects:
        if include_tools:
            projects = {k: v for k, v in projects.items() if k in include_tools}

        elif exclude_tools:
            for toolname in exclude_tools:
                if toolname in projects:
                    projects.pop(toolname)

    e_time = time.time()
    count = 0
    for toolname, prjs in projects.items():
        length = len(prjs)
        count += length

    click.echo("Found projects total {0}, cover {1} toolchains. Used {2:.2f}(s)".format(
        count, len(projects), e_time-s_time))

    for toolname, prjs in projects.items():
        length = len(prjs)
        click.echo(" + {0:<10}  {1}".format(toolname, length))

    return projects, count
