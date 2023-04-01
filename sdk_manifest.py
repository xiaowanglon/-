

import os
import logging
import tempfile
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
from packaging import version


class SDKManifest(object):
    """NXP MCUXpresso SDK Manifest Parser.

    SDKManifest provided interfaces to access attributes data
    from MCUXpresso SDK manifest file.

        >>> mf = SDKManifest("./board_EVK-MIMX8ULP_manifest_v3_8.xml")
        >>> mf.sdk_version
        >>> mf.dump_examples()
    """

    @classmethod
    def find(cls, dirs):
        """Find manifest from given directories."""

        if not isinstance(dirs, list):
            dirs = [dirs]

        manifests = list()
        for dir in dirs:
            for per_file in Path(dir).glob(f"*_manifest*.xml"):
                manifest_obj = cls(str(per_file))
                if manifest_obj is not None:
                    manifests.append(manifest_obj)

        return manifests

    @classmethod
    def find_from_parents(cls, dir):
        """Find manifest from the give path of parent.
        """
        abs_path = os.path.abspath(dir.replace('\\', '/'))
        def _search_dir():
            current_dir = abs_path
            while True:
                parent_dir = os.path.dirname(current_dir)
                # system root
                if parent_dir == current_dir:
                    break
                manifest = cls.find_max_version(parent_dir)
                if manifest:
                    return manifest
                current_dir = parent_dir

        manifest = _search_dir()
        if manifest:
            return manifest

    @classmethod
    def find_max_version(cls, dirs):
        """Find and return the maximum version of manifest from given paths."""
        if isinstance(dirs, str):
            dirs = [dirs]

        manifests = SDKManifest.find(dirs)
        if not manifests:
            return

        return sorted(manifests, key=lambda m: version.parse(m.manifest_version))[-1]

    def __init__(self, filepath):
        self._filepath = filepath
        self._xmlroot = ET.parse(filepath).getroot()
        self._sdk_root = os.path.dirname(filepath)
        self._root_info = self._xmlroot.attrib
        self._sdk_version = self._xmlroot.find('./ksdk').attrib['version']

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        else:
            return False

    @property
    def filepath(self):
        return self._filepath

    @property
    def id(self):
        return self._root_info.get("id")

    @property
    def sdk_version(self):
        return self._sdk_version

    @property
    def sdk_name(self):
        return self._root_info.get("id")

    @property
    def configuration(self):
        return self._root_info.get("configuration")

    @property
    def format_version(self):
        return self._root_info.get("format_version")

    @property
    def manifest_version(self):
        return self._root_info.get("format_version")

    @property
    def schema_location(self):
        return self._root_info.get("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation")

    @property
    def sdk_root(self):
        return self._sdk_root

    @property
    def boards(self):
        xpath = './boards/board'
        nodes = self._xmlroot.findall(xpath)
        return [n.attrib['id'] for n in nodes]

    @property
    def toolchains(self):
        """Return list of toolchains."""
        xpath = './toolchains/toolchain'
        nodes = self._xmlroot.findall(xpath)
        return [n.attrib['id'] for n in nodes]

    @property
    def core_slave_roles_definitions(self):
        nodes = self._xmlroot.findall('./core_slave_roles_definitions/slave_role')
        return [n.attrib for n in nodes]

    @property
    def slave_core(self):
        """Get slave core name."""
        nodes = self._xmlroot.findall('./devices/device/core')
        for node in nodes:
            if node.attrib.get("slave_roles"):
                return node.get("name")
        return

    def _find_example_node(self, key, value):
        """Find example node by attributes:

            - id
            - name
            - path

        """
        assert key in ("id", "name", "path")

        xpath = f'./boards/board/examples/example[@{key}="{value}"]'
        node = self._xmlroot.find(xpath)
        if node is None:
            logging.debug("Cannot found example in manifest, xpath: %s", xpath)
            return

        return node

    def _get_example_info(self, node):
        """Convert XML node to dict.
        """
        if node is None:
            return
        example_info = dict()
        example_info.update(node.attrib)
        xml_node = node.find('./external[@type="xml"]')
        xml_filename = xml_node.find('./files').attrib['mask']
        example_info['example.xml'] = xml_filename
        return example_info

    def find_example(self, example_id):
        """
        Get example info by example_id.
        """
        node = self._find_example_node("id", example_id)
        return self._get_example_info(node)

    def find_example_by_path(self, path):
        """
        Get example info by example path attribute.
        """
        path = path.replace("\\", "/")
        node = self._find_example_node("path", path)
        return self._get_example_info(node)

    def _get_linked_projects(self, example_id, results=None):
        if results is None:
            results = list()

        node = self._find_example_node("id", example_id)

        if node is None:
            return results

        if node in results:
            return results

        parents = self._xmlroot.findall("./boards/board/examples")
        for parent in parents:
            try:
                node.attrib["_index_"] = str(list(parent).index(node))
                break
            except ValueError:
                pass
        results.insert(0, node)
        linked_id = node.attrib.get("linked_projects")

        if not linked_id:
            return results

        return self._get_linked_projects(linked_id, results)

    def find_linked_projects(self, example_id):
        """Return a list of example info. It is ordered by the linked
        relationship.

        For example, primary_example require slave_example, so the first element
        is slave_example.

        Return list example:
            - slave_example
            - primary_example
        Args:
            example_id (str): example id

        Returns:
            List: List of dict
        """
        nodes = self._get_linked_projects(example_id)
        nodes = sorted(nodes, key=lambda x: int(x.attrib["_index_"]))

        # check and re-sort the order by slave core name
        if self.slave_core:
            # get slave project index by matching project id
            # with slave core name
            slave_prj_idx = 0
            for idx, node in enumerate(nodes):
                if node.attrib.get("id").endswith(self.slave_core):
                    slave_prj_idx = idx
                    break

            # swap items in list
            if slave_prj_idx != 0:
                nodes[0], nodes[slave_prj_idx] = nodes[slave_prj_idx], nodes[0]

        return [self._get_example_info(node) for node in nodes]

    def dump_examples(self):
        """
        Return a list of examples.
        """
        xpath = './boards/board/examples/example'
        examples = list()
        for example_node in self._xmlroot.findall(xpath):
            examples.append({
                'toolchain': example_node.attrib['toolchain'].split(" "),
                'path': example_node.attrib['path'],
                'name': example_node.attrib['name'],
                'category': example_node.attrib['category']
            })
        return examples


def merge_manifests(ide_exe, manifest, sdk_root) -> str:
    """Use MCUXpressoIDE merge manifest to sdk_root.

    MCUXpressoIDE in v11.7 support to merge manifest file.
    Github SDK use splitted manifest in multiple repositories.
    Before build github SDK compilers, need to merge manifest in advance.

    Args:
        ide_exe: {str} mcuxpressoide executable path
        manifest: {str} the target manifest to merge
        sdk_root: {str} the sdk root directory

    Returns:
        {str} Path of merged manifest file.


    This API provide a shortcut method to invoke MCUXpressoIDE command line to
    perform the merging work and create merged manifest file.

    IDE Command line Usage:
        mcuxpressoide.exe -application com.nxp.mcuxpresso.headless.application
            -run manifest.merge <path_to_prop_file>/merge.properties -consoleLog

    Property File:
        # This is the location of the manifest XML file that
        # contains references to sub-manifests.
        # The manifest must be inside the repository specified in the repo.location property.
        # NOTE: on Windows you have to use "\\" or "/".
        manifest.xml = <path/to/manifest/file>

        # This is the location where your SDK Git repository has been downloaded.
        # NOTE: on Windows you have to use "\\" or "/".
        repo.location = <path/to/git/repository>

        # This is the location of the merged manifest XML file.
        # NOTE: on Windows you have to use "\\" or "/".
        merged.manifest.xml = <path/to/merged/manifest/file>
    """

    manifest_path = Path(manifest)
    sdk_root_path = Path(sdk_root)
    output = sdk_root_path / f"Merged_{manifest_path.name}"

    with tempfile.NamedTemporaryFile(delete=False, prefix="mcux_", mode='w') as tmp:
        tmp.write(f"manifest.xml = {manifest_path.as_posix()}\n")
        tmp.write(f"repo.location = {sdk_root_path.as_posix()}\n")
        tmp.write(f"merged.manifest.xml = {output.as_posix()}\n")

    commands = [
        ide_exe,
        "--launcher.suppressErrors",
        "-noSplash",
        "-consoleLog",
        "-application",
        "com.nxp.mcuxpresso.headless.application",
        "-run",
        "manifest.merge",
        tmp.name
    ]
    subprocess.check_call(commands)
    logging.info(f"merged-> {output}")
    return output.as_posix()
