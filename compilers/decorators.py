

import os
import glob
import logging

from util import run_command
from compilers.result import Result


def build(func):
    """This function is Decorator and it a will start a new process to exectue the commands which
    comes from Compiler.build_project. When the process finished, it will return the build results.

    Default timeout is None, no timeout

    Returns:
        compilers.BuildResult object.

    Notice:
        For new IDE support, you'd better to add this decorator on the function Compiler.build_project.
    """
    def wraper(*args, **kwargs):
        output = None
        timeout = kwargs.pop('timeout', None)
        _toolchain, _project, _target, _logile = args

        if not kwargs.get('workspace'):
            kwargs['workspace'] = _toolchain.DEFAULT_MCUTK_WORKSPACE + "/" + _toolchain.name

        cmdline = func(*args, **kwargs)
        logging.info("Build command line: %s", cmdline)
        # shell=True: this can resolve windows backslash
        returncode = run_command(
            cmdline,
            shell=True,
            stdout=False,
            timeout=timeout,
            need_raise=True)[0]

        br = _toolchain.parse_build_result(returncode, _logile)
        output = _project.targetsinfo.get(_target)
        br.set_output(output)

        # errors
        if br.result not in (Result.PASSED, Result.Warnings):
            return br

        workspace = kwargs.get('workspace')
        # For eclipse projects, output is located in workspace
        if _toolchain.name in ("mcux") and workspace:
            output_abs = os.path.join(workspace, output)
        else:
            # Assume output file is located in project root
            output_abs = os.path.join(_project.prjdir, output)

        # File exists, return diectly
        if os.path.isfile(output_abs):
            br.set_output(output_abs)
            return br

        if not os.path.exists(output_abs):
            logging.warning("output is not exists: [%s]", output_abs)
            return br

        # Find files in output diectory
        valid_extension = ('.axf', '.elf', '.out', '.hex', '.bin', '.lib', '.a')
        for ext in valid_extension:
            try:
                file_path = glob.glob(output_abs + "/*"+ ext)[0]
                br.set_output(file_path)
                break
            except IndexError:
                pass
        else:
            logging.warning("unable to find output: [%s]", output_abs)

        return br

    return wraper

