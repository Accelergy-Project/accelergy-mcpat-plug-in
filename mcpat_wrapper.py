import os
import io
import copy
import shutil
import subprocess
from datetime import datetime
import xml.etree.ElementTree as ET
from mcpat_components import *

# -------------------------------------------------------------------------------
# McPat Version 1.3 wrapper for generating energy estimations of architecture components
# -------------------------------------------------------------------------------

MCPAT_ACCURACY = 80  # in your metric, please set the accuracy you think McPat's estimations are


components = {
    "fpu_unit": McPatFpuUnit,
    "cache": McPatCache,
}


class McPatWrapper:
    """
    an estimation plug-in
    """

    # -------------------------------------------------------------------------------------
    # Interface functions, function name, input arguments, and output have to adhere
    # -------------------------------------------------------------------------------------
    def __init__(self, clean_output_files=True):
        self.estimator_name = "McPat"
        self.exec_path = search_for_mcpat_exec_path()
        self.cache = {}  # enable data reuse
        self.clean_output_files = clean_output_files

    def primitive_action_supported(self, interface):
        """
        :param interface:
        - contains four keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        3. action_name: string
        4. arguments: dictionary of name: value

        :type interface: dict

        :return return the accuracy if supported, return 0 if not
        :rtype: int

        """
        if interface['class_name'] in components:
            try:
                component = components[interface['class_name']](interface)
            except:
                return 0
            if component.action_supported():
                return MCPAT_ACCURACY
            else:
                return 0
        return 0

    def estimate_energy(self, interface):
        """
        :param interface:
        - contains four keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        3. action_name: string
        4. arguments: dictionary of name: value

       :return the estimated energy
       :rtype float

        """
        component = components[interface['class_name']](interface)
        key = component.key
        if key in self.cache:
            return self.cache[key][0]
        else:
            energy, area = self.query_mcpat(component)
            self.cache[key] = (energy, area)
            return energy

    def primitive_area_supported(self, interface):

        """
        :param interface:
        - contains two keys:
        1. class_name : string
        2. attributes: dictionary of name: value

        :type interface: dict

        :return return the accuracy if supported, return 0 if not
        :rtype: int

        """
        if interface['class_name'] in components:
            try:
                component = components[interface['class_name']](interface)
            except:
                return 0
            if component.attr_supported():
                return MCPAT_ACCURACY
            else:
                return 0
        return 0

    def estimate_area(self, interface):
        """
        :param interface:
        - contains two keys:
        1. class_name : string
        2. attributes: dictionary of name: value

        :type interface: dict

        :return the estimated area
        :rtype: float

        """
        component = components[interface['class_name']](interface)
        key = component.key
        if key in self.cache:
            return self.cache[key][1]
        else:
            energy, area = self.query_mcpat(component)
            self.cache[key] = (energy, area)
            return area

    def query_mcpat(self, component):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        properties_path = os.path.join(dir_path, "properties-%s.xml" % component.name)
        output_path = os.path.join(dir_path, "mcpat-%s" % component.name)
        properties = Properties()
        for path, value in component.properties.items():
            success = properties.replace(path, value)
            if not success:
                raise Exception("Could not locate property %s" % path)
        properties.write(properties_path)

        # call mcpat
        exec_list = [self.exec_path, '-infile', properties_path, "-print_level", "5"]
        with open(output_path, "w") as file:
            subprocess.call(exec_list, stdout=file)

        # parse mcpat output
        with open(output_path, "r") as file:
            output_string = file.read()
            pattern = re.compile(component.mcpat_name + r"[\w\W]*?Area = (\d*.\d*)[\w\W]*?Runtime Dynamic = (\d*.\d*)")
            match = pattern.search(output_string)
            if match:
                energy = float(match.group(2)) * 10 ** 12 / (
                        int(component.clockrate) * 10 ** 6)  # W to pJ conversion
                area = float(match.group(1))
            else:
                raise Exception("Unable to find component " + component.mcpat_name + " in McPat output")
        if self.clean_output_files:
            os.remove(properties_path)
            os.remove(output_path)
        return energy, area


def search_for_mcpat_exec_path():
    # search the current directory first, top-down walk
    this_dir, this_filename = os.path.split(__file__)
    for root, directories, file_names in os.walk(this_dir):
        if 'obj_dbg' not in root:
            for file_name in file_names:
                if file_name == 'mcpat':
                    mcpat_exec_path = root + os.sep + file_name
                    return mcpat_exec_path

    # search the PATH variable: search the directories provided in the PATH variable. top-down walk
    PATH_lst = os.environ['PATH'].split(os.pathsep)
    for path in PATH_lst:
        for root, directories, file_names in os.walk(os.path.abspath(path)):
            for file_name in file_names:
                if file_name == 'mcpat':
                    mcpat_exec_path = root + os.sep + file_name
                    return mcpat_exec_path


class Properties:

    tree_template = ET.parse("properties.xml")

    def __init__(self):
        self.tree = copy.deepcopy(self.tree_template)
        self.root = self.tree.getroot()

    def replace(self, path, value):
        query = "."
        for name in path.split("."):
            query += "/*[@name='%s']" % name
        node = self.root.find(query)
        if node is not None:
            node.attrib["value"] = str(value)
            return True
        else:
            return False

    def write(self, path):
        self.tree.write(path, encoding="utf8")
