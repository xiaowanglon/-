import os
import re
import shutil

from xml.etree import cElementTree as ET
from compilers.projectbase import ProjectBase
from exceptions import ProjectNotFound



def generate_build_cmdline(executor, workspace, project_root, project_name,
    target='all', application='org.eclipse.cdt.managedbuilder.core.headlessbuild', cleanbuild=True):
    """Generate and return C/C++ build command line for Eclipse project. Return type list of strings.

    This is a common interface for generatl eclipse project.

    Eclipse runtime documentation:
    https://help.eclipse.org/kepler/index.jsp?topic=%2Forg.eclipse.platform.doc.isv%2Freference%2Fmisc%2Fruntime-options.html&anchor=eclipseproduct


    Note about eclipse command line mode.

    eclipsec --launcher.suppressErrors -nosplash
        -application {org.eclipse.cdt.managedbuilder.core.headlessbuild|other applications}
        [-cleanBuild|-build] {project_name_reg_ex/config_name_reg_ex | all}
        [-import|-importAll] {[uri:/]/path/to/project}}
        -data {workspace path}

        =======================     =======================
        Parameter                   Description
        =======================     =======================
        -application applicationId  The application to run. Applications are declared by plug-ins supplying extensions to the org.eclipse.core.runtime.applications extension point. This argument is
                                    typically not needed. If specified, the value overrides the value supplied by the configuration. If not specified, the Eclipse Workbench is run.
        --launcher.suppressErrors   If specified the executable will not display any error or message dialogs. This is useful if the executable is being used in an unattended situation
        -nosplash                   Controls whether or not the splash screen is shown.
        -data workspacePath         The path of the workspace on which to run the Eclipse platform. The workspace location is also the default location for projects. Relative paths are interpreted.
                                    relative to the directory that Eclipse was started from.
        -nosplash                   Runs the platform without putting up the splash screen.
        -import                     {[uri:/]/path/to/project} -- Import projects under URI.
        -importAll                  {[uri:/]/path/to/projectTreeURI} -- Import all projects under URI.
        -build                      {project_name_reg_ex{/config_reg_ex} | all} -- Build projects.
        -cleanBuild                 {project_name_reg_ex{/config_reg_ex} | all} -- Clean and  build projects.
        -I                          {include_path} -- additional include_path to add to tools
        -include                    {include_file} -- additional include_file to pass to tools
        -D                          {prepoc_define} -- addition preprocessor defines to pass to the tools
        -E                          {var=value} -- replace/add value to environment variable when running all tools
        -Ea                         {var=value} -- append value to environment variable when running all tools
        -Ep                         {var=value} -- prepend value to environment variable when running all tools
        -Er                         {var} -- remove/unset the given environment variable
        -T                          {toolid} {optionid=value} -- replace a tool option value in each configuration built
        -Ta                         {toolid} {optionid=value} -- append to a tool option value in each configuration built
        -Tp                         {toolid} {optionid=value} -- prepend to a tool option value in each configuration built
        -Tr                         {toolid} {optionid=value} -- remove a tool option value in each configuration built
    """
    # Note:
    # If project already in workspace, eclipse will alert an error and exit.
    # To resolve this pain, force remove tree '.metadata\.plugins\org.eclipse.core.resources'
    if os.path.exists(workspace):
        eclipse_core_resources = os.path.join(
            workspace, '.metadata/.plugins/org.eclipse.core.resources')

        if os.path.exists(eclipse_core_resources):
            shutil.rmtree(eclipse_core_resources, ignore_errors=True)

    project_root = os.path.abspath(project_root)
    cmd = [
        executor,
        "--launcher.suppressErrors",
        "-noSplash",
        "-consoleLog",
        "-application",
        application,
        "-data",
        workspace,
        "-importAll",
        project_root
    ]

    if cleanbuild:
        cmd.append("-cleanBuild")
        cmd.append(f"{project_name}/{target}")
    return cmd



class Project(ProjectBase):
    """A simple parser for Eclipse C/C++ Project.
    """

    PRJ_GLOB_PATTERN = ".cproject"

    def __init__(self, path, *args, **kwargs):
        super(Project, self).__init__(path, **kwargs)
        self._name = None
        self._targets = dict()
        self._conf = dict()
        self.cproject = None
        if self.prjpath.endswith('.project') or self.prjpath.endswith('.cproject'):
            self.parse(self.prjpath)

    def parse_project(self, path):
        """ Parse .project """

        xml_root = ET.parse(path).getroot()
        return xml_root.find('./name').text.strip()

    def parse_cproject(self, cpath):
        """ Parse .cproject """
        self.cproject = ET.parse(cpath).getroot()
        var_pattern = re.compile(r"^\$\{.*\}/")
        targets = {}

        for per_node in self.cproject.findall('.//configuration[@buildArtefactType]'):
            target_name = per_node.attrib.get('name').strip()
            extension = per_node.attrib.get('artifactExtension', '').strip()
            artifact_name = per_node.attrib.get('artifactName').strip()
            if artifact_name == "${ProjName}":
                artifact_name = self._name

            output_name = artifact_name + '.' + extension
            output_dir = target_name
            builder_node = per_node.find(".//builder[@buildPath]")
            if builder_node is not None:
                output_dir = var_pattern.sub('', builder_node.attrib["buildPath"])
            targets[target_name] = output_dir + "/" + output_name

        return targets

    def parse(self, path):
        """ Main entry to parse eclipse project. """

        if not path.endswith('.project'):
            path = os.path.join(self.prjdir, '.project')

        cpath = os.path.join(self.prjdir, '.cproject')
        self._name = self.parse_project(path)
        self._conf = self.parse_cproject(cpath)
        self._targets = self._conf.keys()

    @property
    def name(self):
        """Return the application name

        Returns:
            string --- app name
        """
        return self._name

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
