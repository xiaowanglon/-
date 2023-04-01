
import os
import logging
import tempfile
from xml.etree import cElementTree as ET
from pathlib import Path
from compilers import eclipse
from sdk_manifest import SDKManifest
from exceptions import ProjectNotFound, ProjectParserError


class Project(eclipse.Project):
    """MCUXpresso SDK and projects parser tool."""

    PRJ_GLOB_PATTERN = ('*.xml', ".cproject")


    def __init__(self, prjpath, sdk_root=None, **kwargs):
        """MCUXPressoIDE project constructor.

        Arguments:
            prjpath {str} -- path to <name>.xml

        Keyword Arguments:
            sdk_root {str} -- path to sdk package root, default {None} that will be loaded from xml.
        """
        self.board = None
        self._is_package = False
        self._sdk_root = sdk_root
        self._name = ''
        self._targets = None
        self._sdkmanifest = Project.SDK_MANIFEST
        self._example_id = None
        self._example_xml = None
        self._nature = 'org.eclipse.cdt.core.cnature'
        self.build_properties = None

        super(Project, self).__init__(prjpath, **kwargs)
        # eclipse project
        self._is_package = not (prjpath.endswith('.project') or prjpath.endswith('.cproject'))

        if self._is_package:
            self._load_from_sdk_package(prjpath)
            self._properties_init()
            ET.register_namespace("ksdk", "http://nxp.com/ksdk/2.0/ksdk_manifest_v3.0.xsd")
            self._example_xml = ET.parse(prjpath)
        else:
            prj_root = Path(prjpath).parent
            with open(prj_root / ".project" ) as fobj:
                content = fobj.read()
                if not ('mcux' in content or 'mcuxpresso' in content):
                    raise ProjectNotFound('Not mcuxpresso project')

        if self.sdkmanifest and not self.is_enabled:
            raise ProjectNotFound("Not enabled in SDK Manifest: %s" % self.sdkmanifest)

    @property
    def is_enabled(self):
        """Identify the example if is enabled(SDK package only).
        """
        if not self.is_package:
            return True

        # check manifest: this exmaple is enabled for mcux
        example_info = self.sdkmanifest.find_example(self._example_id)
        if not example_info:
            return False
        # manifest version 3.1
        if self.sdkmanifest.manifest_version == "3.1":
            return True

        return "mcux" in example_info.get("toolchain", "")

    @property
    def sdkmanifest(self):
        """Getter for SDKMainfest object"""
        return self._sdkmanifest

    @sdkmanifest.setter
    def sdkmanifest(self, value):
        """Setter for SDKMainfest object"""
        if value is None:
            return

        if not isinstance(value, SDKManifest):
            raise ValueError("Must be a SDKManifest object")

        self._sdkmanifest = value


    @property
    def is_package(self):
        """Package project or standard eclipse project"""
        return self._is_package

    def parse_cproject(self, cpath):
        """Override default .cproject parser.
        MCUXpressoIDE saved SDK info into:
            .//storageModule[@moduleId=\"com.nxp.mcuxpresso.core.datamodels\"]
        """
        conf = super(Project, self).parse_cproject(cpath)
        storage_module = self.cproject\
            .find(".//storageModule[@moduleId=\"com.nxp.mcuxpresso.core.datamodels\"]")
        if storage_module is not None:
            board_id_node = storage_module.find(".//boardId")
            if board_id_node is not None:
                self.board = board_id_node.text
        return conf

    def _load_from_eclipse_project(self, path):
        """Load from Eclipse C/C++ project"""
        self.parse(path)

    def _load_from_sdk_package(self, path):
        """Load from SDK <app>.xml and *_manifest*.xml.
            1. Parse <app>.xml to get manifest.xml,
            2. Get related information from manifest.
        """

        self._targets = self._conf.keys()
        try:
            xmlroot = ET.parse(path).getroot()
            example_node = xmlroot.find('./example')

            if example_node is None:
                raise ProjectNotFound(f'Unable to find <example> node. {path}')

        except (IOError, ValueError) as err:
            raise ProjectNotFound(f'parse xml error: {err} ,path: {path}')

        self._example_id = example_node.attrib.get('id')
        # in some situation, the name attribute is not too simple
        # that is not full project name for mcux, we have to use a workaround
        # to get project name from path.
        example_name = example_node.attrib.get('name')
        xml_name = os.path.basename(path).replace('.xml', '')
        if example_name in xml_name:
            self._name = example_name
        else:
            self._name = xml_name

        try:
            self._nature = example_node.find('projects/project[@nature]').attrib.get('nature')
        except:
            pass

        if not self._example_id:
            raise ProjectParserError(f'None id in exmaple node! {self.prjpath}')


        self._conf = {
            'Debug': f'{self._example_id}/Debug/',
            'Release': f'{self._example_id}/Release/'
        }
        if self.sdkmanifest:
            return

        # find sdk manifest from parent folders
        self.sdkmanifest = SDKManifest.find_from_parents(self.prjdir)

        if self.sdkmanifest:
            Project.SDK_MANIFEST = self.sdkmanifest
            return

        raise ProjectParserError("Unable to find SDK Manifest!")

    def _properties_init(self):
        """Init build properties variable.

        sdk.location = D:/Users/B46681/Desktop/SDK_2.0_MK64FN1M0xxx12-drop4
            This is the location where your SDK have been downloaded.
            You can use either zip or folder containing the SDK
            Please remember that if you want to create linked resources into your
            project(i.e. standalone = false) you need to use a folder instead of a zip.
            NOTE: on Windows you have to use "//" or "/".

        example.xml = D:/../hello_world/mcux/hello_world.xml
            If adding the "example.xml" property, the examples are retrieved from that
            specific file and shall valid against the used SDK
            NOTE: on Windows you have to use "//" or "/".

        nature = org.eclipse.cdt.core.cnature
            This represents the nature of your project (i.e. C or C++)
            It can be:
                - org.eclipse.cdt.core.cnature for C projects
                - org.eclipse.cdt.core.ccnature for C++ projects
                (Please remember that the example your're going to create shall support the
                C++ nature)

        standalone = true
            If true, it will copy the files from the SDK, otherwise it will link them.
            Note: linked resources will be only created if the SDK is provided as a folder

        project.build = true
            If true, the project will be compiled, otherwise the project is only created.

        clean.workspace = true
            True, if you want to clear the workspace used, false otherwise

        build.all = false
            If true, all the examples from all the SDK will be created, otherwise you need
            specify the SDK name

        skip.default = false
            If true, skip the default SDKPackages folder and all its content
            Default is false

        sdk.name = SDK_2.0_MK64FN1M0xxx12
            The SDK name (i.e. the folder/file name without extension)
            NOTE: only used when build.all = false

        board.id = frdmk64f
            The board id as for the manifest definition
            NOTE: only used when build.all = false

        Other Settings:
            verbose = true
                If true, more info will be provided using stdout

            indexer = false
                If true, enable the CDT indexer, false otherwise

            project.build.log = true
                If true, show the CDT build log, false otherwise

            simple.project.name = true

        """
        self.build_properties = {
            'sdk.location': None,
            'example.xml': None,
            'nature': 'org.eclipse.cdt.core.cnature',
            'standalone': 'true',
            'project.build': 'true',
            'clean.workspace': 'false',
            'build.all': 'false',
            'build.config': 'debug',
            'simple.project.name': 'false',
            'use.other.files': 'true ',
            'skip.default': 'true',
            'sdk.name': None,
            'board.id': '',
            'verbose': 'false',
            'indexer': 'false',
            'use.io.console': 'false',
            'project.build.log': 'true',
            'use.semihost.hardfault.handler': 'true'
        }

    def gen_properties(self, target, loc=None):
        """Return a file path for properties file.

        Arguments:
            target -- {string} target configuration
            loc -- {string} the location to place the new geneated file,
            default is None means system tempfile.

        """
        # boardid will effect workspace path
        board_ids = self.sdkmanifest.boards
        boardid = self._example_id.replace("_" + self._name, '')
        if boardid not in board_ids:
            boardid = board_ids[0]

        logging.info("SDK Manifest Version: %s", self.sdkmanifest.manifest_version)
        # There may be multiple example.xml, to use correct xml we should
        # look up the manifest file.
        example_info = self.sdkmanifest.find_example(self._example_id)
        example_xml_filename = example_info.get('example.xml')
        if example_xml_filename:
            example_xml = os.path.join(self.prjdir, example_xml_filename)
        else:
            # Compatible with old SDK package.
            example_xml = self.prjpath

        self.setproperties("example.xml", os.path.abspath(example_xml).replace('\\', '/'))
        self.setproperties("sdk.location", self.sdkmanifest.sdk_root.replace('\\', '/'))
        self.setproperties("nature", self.nature)
        self.setproperties("sdk.name", self.sdkmanifest.sdk_name)
        self.setproperties("board.id", boardid)
        self.setproperties("build.config", target)

        with tempfile.NamedTemporaryFile(dir=loc, delete=False, prefix="mcux_", mode='w') as f:
            for per_property, value in self.build_properties.items():
                f.writelines(f"{per_property} = {value}\r\n")

            properties_file = f.name

        logging.debug('properties file: %s', properties_file)
        return properties_file

    def setproperties(self, attrib, value):
        """ Set the value of self.build_properties"""

        self.build_properties[attrib] = value

    @property
    def nature(self):
        """Retrun used nature"""
        return self._nature

    @property
    def targets(self):
        """Return all targets name

        Returns:
            list -- a list of targets
        """
        if self._targets:
            return list(self._targets)

        return ['Debug', 'Release']

    @property
    def name(self):
        """Return the application name

        Returns:
            string --- app name
        """
        return self._name

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
        _dict = {
            'toolchain': self.idename,
            'targets': self.targets,
            'project': self.prjpath,
            'name': self.name
        }
        if self.board:
            _dict["board"] = self.board

        return _dict
