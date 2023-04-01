


class ExpectFail(Exception):
    pass


class ProjectNotFound(Exception):
    pass

class ProjectParserError(Exception):
    pass


class ToolchainError(Exception):
    pass


class InvalidTarget(Exception):
    pass


class InstallError(Exception):
    pass


class ReadElfError(Exception):
    pass


class ProcessTimeout(Exception):
    pass

class GDBServerStartupError(Exception):
    pass

class CmsisPackIssue(Exception):
    pass


