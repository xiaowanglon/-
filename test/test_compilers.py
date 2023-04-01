from unittest import TestCase
from compilers import compilerfactory


class TestCompiler(TestCase):
    def test_mcux_info(self):
        mcux_module = compilerfactory("mcux")
        mcux_path, version = mcux_module.get_latest_tool()
        mcux = mcux_module(mcux_path, version=version)
        assert mcux.path
        print(mcux.version)
        print(mcux.name)



