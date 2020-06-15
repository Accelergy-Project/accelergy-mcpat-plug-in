import os
import re
import copy
import subprocess
import xml.etree.ElementTree as ET

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
        action_name = component.interface["action_name"]
        properties_path = os.path.join(dir_path, "properties-%s-%s.xml" % (component.name, action_name))
        output_path = os.path.join(dir_path, "mcpat-%s-%s" % (component.name, action_name))
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
    dir_path = os.path.dirname(os.path.realpath(__file__))
    tree_template = ET.parse(os.path.join(dir_path, "properties.xml"))

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


class McPatComponent:
    """
    Base component to query McPat
    """

    base_properties = {
        "system.number_of_cores": 1,
        "system.number_of_L1Directories": 1,
        "system.number_of_L2Directories": 1,
        "system.number_of_L2s": 1,
    }

    def __init__(self, interface):
        self.interface = interface
        self.properties = self.base_properties.copy()

        tech_node = interface['attributes']['technology']  # technology in nm
        if type(tech_node) == str:
            tech_node = re.compile(r"(\d*)nm").match(tech_node.lower()).group(1)
        self.properties["system.core_tech_node"] = tech_node
        self.tech_node = tech_node

        clockrate = interface['attributes']['clockrate']  # clockrate in mHz
        if type(clockrate) == str:
            clockrate = re.compile(r"(\d*)mhz").match(clockrate.lower()).group(1)
        self.properties["system.target_core_clockrate"] = clockrate
        self.properties["system.core0.clock_rate"] = clockrate
        self.clockrate = clockrate


class McPatFpuUnit(McPatComponent):
    """
    component: fpu_unit
    actions  : fp_instruction
    """

    def __init__(self, interface):
        super().__init__(interface)
        self.name = "fpu_unit"
        self.mcpat_name = "Floating Point Units"
        self.key = 'fpu_unit', self.tech_node, self.clockrate

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] == "fp_instruction"


# TODO add dcache
class McPatCache(McPatComponent):
    """
    component  : cache
    cache types: icache
    actions    : read_access, read_miss
    """

    def __init__(self, interface):
        super().__init__(interface)
        datawidth = interface["attributes"]["datawidth"]
        size = interface["attributes"]["size"]                            # size in bytes
        block_size = interface["attributes"]["block_size"]                # block size in bytes
        associativity = interface["attributes"]["associativity"]          # cache associativity
        data_latency = interface["attributes"]["data_latency"]            # data latency in cycles
        mshr_size = interface["attributes"]["mshr_size"]                  # maximum outstanding requests
        write_buffer_size = interface["attributes"]["write_buffer_size"]  # write buffer size
        n_banks = interface["attributes"]["n_banks"]                      # number of cache banks
        read_access, read_misses, write_access, write_misses = 0, 0, 0, 0
        action_name = self.interface["action_name"]
        if action_name == "read_access":
            read_access = 1
        elif action_name == "read_miss":
            read_misses = 1
        elif action_name == "write_access":
            write_access = 1
        elif action_name == "write_miss":
            write_misses = 1


        self.properties["system.total_cycles"] = 1
        self.properties["system.busy_cycles"] = 1

        cache_type = self.interface["attributes"]["cache_type"]
        self.properties["system.core0.%s.%s_config" % (cache_type, cache_type)] = \
            "%s, %s, %s, %s, 1, %s, %s, 0" % (size, block_size, associativity, n_banks, data_latency, datawidth)
        self.properties["system.core0.%s.buffer_sizes" % cache_type] = \
            "%s, 4, %s, 0" % (mshr_size, write_buffer_size)
        self.properties["system.core0.%s.read_accesses" % cache_type] = read_access
        self.properties["system.core0.%s.read_misses" % cache_type] = read_misses
        self.properties["system.core0.%s.conflicts" % cache_type] = 0
        if cache_type != "icache":
            self.properties["system.core0.%s.write_accesses" % cache_type] = write_access
            self.properties["system.core0.%s.write_misses" % cache_type] = write_misses

        self.name = cache_type
        self.key = (cache_type, self.interface["action_name"], self.tech_node, self.clockrate,
                    datawidth, size, block_size, associativity, data_latency, mshr_size,
                    write_buffer_size, n_banks)
        if cache_type == "icache":
            self.mcpat_name = "Instruction Cache"
        elif cache_type == "dcache":
            self.mcpat_name = "Data Cache"


    def attr_supported(self):
        return self.interface["attributes"]["cache_type"] in ["icache", "dcache"]

    def action_supported(self):
        cache_type = self.interface["attributes"]["cache_type"]
        if cache_type == "icache":
            return self.interface["action_name"] in ["read_access", "read_miss"]
        elif cache_type == "dcache":
            return self.interface["action_name"] in ["read_access", "read_miss", "write_access", "write_miss"]
        else:
            return False


components = {
    "fpu_unit": McPatFpuUnit,
    "cache": McPatCache,
}
