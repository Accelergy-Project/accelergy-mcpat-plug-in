import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime

# -------------------------------------------------------------------------------
# McPat Version 1.3 wrapper for generating energy estimations of architecture components
# -------------------------------------------------------------------------------

MCPAT_ACCURACY = 80  # in your metric, please set the accuracy you think McPat's estimations are


class McPatWrapper:
    """
    an estimation plug-in
    """

    # -------------------------------------------------------------------------------------
    # Interface functions, function name, input arguments, and output have to adhere
    # -------------------------------------------------------------------------------------
    def __init__(self, output_prefix=''):
        self.estimator_name = "McPat"
        self.output_prefix = output_prefix
        self.exec_path = self.search_for_mcpat_exec_path()
        self.cache = {}  # enable data reuse
        self.components = {
            "fpu_unit": McPatFpuUnit,
            "cache": McPatCache,
        }

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
        if interface['class_name'] in self.components:
            component = self.components[interface['class_name']](interface, self)
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
        component = self.components[interface['class_name']](interface, self)
        key = component.get_key()
        if key in self.cache:
            return self.cache[key][0]
        else:
            energy = component.get_value("energy")
            area = component.get_value("area")
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
        if interface['class_name'] in self.components:
            component = self.components[interface['class_name']](interface, self)
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
        component = self.components[interface['class_name']](interface, self)
        key = component.get_key()
        if key in self.cache:
            return self.cache[key][1]
        else:
            energy = component.get_value("energy")
            area = component.get_value("area")
            self.cache[key] = (energy, area)
            return area

    def search_for_mcpat_exec_path(self):
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


class McPatComponent:
    """
    Base component to query McPat
    """

    def __init__(self, interface, wrapper):
        self.interface = interface
        self.wrapper = wrapper
        tech_node = interface['attributes']['technology']  # technology in nm
        if type(tech_node) == str:
            pattern = re.compile(r"(\d*)nm")
            match = pattern.match(tech_node.lower())
            if match is not None:
                tech_node = int(match.group(1))
            else:
                raise Exception("Unable to parse technology" + tech_node)
        clockrate = interface['attributes']['clockrate']  # clockrate in mHz
        if type(clockrate) == str:
            pattern = re.compile(r"(\d*)mhz")
            match = pattern.match(clockrate.lower())
            if match is not None:
                clockrate = int(match.group(1))
            else:
                raise Exception("Unable to parse clockrate" + clockrate)
        self.param = {
            "TECH_NODE": tech_node,
            "CLOCKRATE": clockrate,
        }
        self.area = None
        self.energy = None

    def query(self, template_type, match_string):
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates/" + template_type + ".xml")
        input_path = self.wrapper.output_prefix + template_type + ".xml"

        # substitute parameter values
        with open(template_path, "r") as file:
            template = file.read()
        for key, value in self.param.items():
            template = re.sub(r"\$" + key, str(value), template)
        with open(input_path, "w") as file:
            file.write(template)

        # create temporary output for McPat
        output_stream, output_path = tempfile.mkstemp()
        exec_list = [self.wrapper.exec_path, '-infile', input_path, "-print_level", "5"]
        subprocess.call(exec_list, stdout=output_stream)
        os.close(output_stream)

        # log input to McPat
        temp_dir = tempfile.gettempdir()
        accelergy_tmp_dir = os.path.join(temp_dir, 'accelergy')
        if os.path.exists(accelergy_tmp_dir):
            if len(os.listdir(accelergy_tmp_dir)) > 50:  # clean up the dir if there are more than 50 files
                shutil.rmtree(accelergy_tmp_dir, ignore_errors=True)
                os.mkdir(accelergy_tmp_dir)
        else:
            os.mkdir(accelergy_tmp_dir)
        shutil.copy(input_path, os.path.join(accelergy_tmp_dir,
                                             template_type + '_' + datetime.now().strftime("%m_%d_%H_%M_%S") + ".xml"))

        # extract energy and area
        with open(output_path, "r") as file:
            output_string = file.read()
            pattern = re.compile(match_string + r"[\w\W]*?Area = (\d*.\d*)[\w\W]*?Runtime Dynamic = (\d*.\d*)")
            match = pattern.search(output_string)
            if match is not None:
                self.energy = float(match.group(2)) * 10 ** 12 / (
                            self.param["CLOCKRATE"] * 10 ** 6)  # W to pJ conversion
                self.area = float(match.group(1))
            else:
                raise Exception("Unable to find field " + match_string + " in McPat output")

        # clean up temp files
        os.remove(output_path)
        os.remove(input_path)


class McPatFpuUnit(McPatComponent):
    """
    component: fpu_unit
    actions  : fp_instruction
    """

    def __init__(self, interface, wrapper):
        super().__init__(interface, wrapper)

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] == "fp_instruction"

    def get_key(self):
        return 'fpu_unit', self.param["TECH_NODE"], self.param["CLOCKRATE"]

    def get_value(self, param):
        if self.energy is None:
            self.query("fpu", "Floating Point Units")
        if param == "energy":
            return self.energy
        if param == "area":
            return self.area
        else:
            raise Exception("Query parameter " + param + " invalid")


# TODO add dcache
class McPatCache(McPatComponent):
    """
    component  : cache
    cache types: icache
    actions    : read_access, read_miss
    """

    def __init__(self, interface, wrapper):
        super().__init__(interface, wrapper)
        self.param["SIZE"] = interface["attributes"]["size"]               # size in bytes
        self.param["BLOCK_WIDTH"] = interface["attributes"]["block_size"]  # block size in bytes
        self.param["ASSOC"] = interface["attributes"]["associativity"]     # cache associativity
        self.param["LATENCY"] = interface["attributes"]["hit_latency"]     # hit latency in cycles
        self.param["MSHRS"] = interface["attributes"]["mshrs"]             # maximum outstanding requests
        self.param["READ_ACCESSES"] = 0
        self.param["READ_MISSES"] = 0
        if self.interface["action_name"] == "read_access":
            self.param["READ_ACCESSES"] = 1
        if self.interface["action_name"] == "read_miss":
            self.param["READ_MISSES"] = 1

    def attr_supported(self):
        return self.interface["attributes"]["cache_type"] == "icache"

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] in ["read_access", "read_miss"]

    def get_key(self):
        if self.interface["attributes"]["cache_type"] == "icache":
            return ("icache", self.interface["action_name"], self.param["TECH_NODE"],
                    self.param["CLOCKRATE"], self.param["SIZE"], self.param["BLOCK_WIDTH"],
                    self.param["ASSOC"], self.param["LATENCY"], self.param["MSHRS"])
        else:
            raise Exception("Cache type " + self.interface["attributes"]["cache_type"] + " not supported")

    def get_value(self, param):
        if self.energy is None:
            if self.interface["attributes"]["cache_type"] == "icache":
                self.query("icache", "Instruction Cache")
            else:
                raise Exception("Cache type " + self.interface["attributes"]["cache_type"] + " not supported")
        if param == "energy":
            return self.energy
        if param == "area":
            return self.area
        else:
            raise Exception("Query parameter " + param + " invalid")
