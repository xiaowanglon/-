#

#

import os
import re
import logging
import platform
from packaging import version

from compilers import eclipse
from compilers import IDEBase, BuildResult


class Compiler(IDEBase):
    """Wrapped MCUXpressoIDE.

    MCUXpressoIDE exitcode Definition:
    --------------
        - 0 - no errors
        - 1 - no application has been found (i.e. -run option is wrong)
        - 2 - a hard internal error has occurred
        - 3 - the command line -run option returned with errors
            (e.g., validation, project creation, project build, etc...)
        - 4 - the command line -run option returned with warnings
            (e.g., validation, compile, link, etc...)
    """

    EXITCODE = {
        0 : 'PASS',
        1 : 'Compiler Error',
        2 : 'Internal Errors',
        3 : 'Errors',
        4 : 'Warnings'
    }

    BUILD_PROPERTY_PREFIX = "mcux_build_"

    OSLIST = ['Windows', "Linux", "Darwin"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.builder = get_executable(self.path)

    @property
    def is_ready(self):
        return os.path.exists(self.builder)

    def get_build_command_line(self, project, target, logfile, **kwargs):
        """Return a string about the build command line.

        Arguments:
            project {mcux.Project} -- mcux project object
            target {str} -- target name
            logfile {str} -- log file path
            workspace {str} -- workspace directory

        Returns:
            string -- build commandline

        MCUXpressoIDE command line:

        - SDK Packages mode:

        Usage: <install path>/mcuxpressoide
            -application com.nxp.mcuxpresso.headless.application
            -consoleLog -noSplash
            -data             <path/to/your/workspace/folder/to/use>
            [-run  <command>  <path/to/your/build.properties> | -help <command>]

            Available commands:
                sdk.validate            Validate content of SDK(s)
                partsupport.install     Install part support from one or more SDK.
                toolchain.options       Show the supported options in the MCUXpressoIDE toolchains
                example.build           Create/build examples from one or more SDK or an examples
                                        XML definition file.
                list.probes             List all supported probes
                project.build           Create/build projects from one or more SDK.
                example.options         Check examples options.
                list.parts              List all installed MCUs

        """
        workspace = kwargs.get('workspace')
        properties_file = kwargs.get("properties_file")

        user_properties = dict()
        for opt, value in kwargs.items():
            if opt.startswith(self.BUILD_PROPERTY_PREFIX):
                user_properties[opt.replace(self.BUILD_PROPERTY_PREFIX, "")] = value

        if not os.path.exists(workspace):
            os.makedirs(workspace)

        # SDK package
        if project.is_package:

            if properties_file:
                logging.debug(f"use specificed properties file: {properties_file}")

            else:
                if user_properties:
                    project.build_properties.update(user_properties)
                # generate properties file
                properties_file = project.gen_properties(target)

            buildcmd = [
                self.builder,
                "--launcher.suppressErrors",
                "-noSplash",
                "-consoleLog",
                "-application",
                "com.nxp.mcuxpresso.headless.application",
                "-data",
                workspace,
                "-run",
                "example.build",
                properties_file
            ]

        # eclipse project
        else:
            buildcmd = eclipse.generate_build_cmdline(
                self.builder,
                workspace,
                project.prjdir,
                project.name,
                target,
                cleanbuild=False)

        if logfile:
            buildcmd.append(f'>> "{logfile}" 2>&1')

        return " ".join(buildcmd)


    @classmethod
    def get_latest_tool(cls):
        """
        Discover installed instances.
        """
        supported_os = {
            "Windows": ("C:/nxp/", "MCUXpressoIDE_"),
            "Linux": ("/usr/local/", "mcuxpressoide-"),
            "Darwin": ("/Applications/", "MCUXpressoIDE_")
        }

        ins_info = supported_os.get(platform.system())
        if not ins_info:
            logging.warning("mcux: unsupported platform!")
            return

        parent_dir, prefix_key = ins_info
        if not os.path.exists(parent_dir):
            return

        mcux_pool = [path for path in os.listdir(parent_dir) if "mcuxpressoide" in path.lower()]
        mcux_tools = [(parent_dir + path, path.replace(prefix_key, "")) for path in mcux_pool]
        print(mcux_tools)
        #versions = [(ver[0], version.parse(str(ver[1]))) for ver in mcux_tools]

        return mcux_tools[-1]

    @staticmethod
    def parse_build_result(exitcode, logfile=None):
        """Parse mcuxpressoide build result.
        """
        status = Compiler.EXITCODE.get(exitcode, "Errors")

        # To exculde bellow IDE warnigs by parse build logs:
        # WARNING: The project name
        # 'evkmimxrt1020_dev_composite_hid_mouse_hid_keyboard_freertos'
        # exceed maximum length of '56' characters: please check your category and/or name
        # fields in the example XML definition.
        if exitcode == 4 and logfile and os.path.exists(logfile):
            with open(logfile, "r") as fobj:
                content = fobj.read()

            warning_pattern = r"Build Finished\. 0 errors, 0 warnings\."
            if re.compile(warning_pattern).search(content):
                return BuildResult.map("PASS")

        return BuildResult.map(status)


def get_executable(path):
    """Return mcuxpresso executable"""

    osname = platform.system()

    if osname == "Windows":
        return os.path.join(path, "ide/mcuxpressoidec.exe").replace("\\", "/")

    elif osname == "Linux":
        return os.path.join(path, "ide/mcuxpressoide")

    elif osname == "Darwin":
        return os.path.join(path, "ide/MCUXpressoIDE.app/Contents/MacOS/mcuxpressoide")
