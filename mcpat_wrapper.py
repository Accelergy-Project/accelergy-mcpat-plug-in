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
            energy = 0
            area = 0
            for mcpat_pattern in component.mcpat_patterns:
                pattern = re.compile(mcpat_pattern + r"[\w\W]*?Area = (\d*.\d*)[\w\W]*?Runtime Dynamic = (\d*.\d*)")
                match = pattern.search(output_string)
                if match:
                    energy += float(match.group(2)) * 10 ** 12 / (
                              int(component.clockrate) * 10 ** 6)  # W to pJ conversion
                    area += float(match.group(1))
                else:
                    raise Exception("Unable to find component " + mcpat_pattern + " in McPat output")
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


class McPatFuncUnit(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        self.datawidth = interface["attributes"]["datawidth"]
        self.type = interface["attributes"]["type"]

        fpu_access, int_alu_access, mul_alu_access = 0, 0, 0
        if self.type == "fpu":
            fpu_access = 1
        elif self.type == "int_alu":
            int_alu_access = 1
        else:
            mul_alu_access = 1

        self.properties["system.total_cycles"] = 1
        self.properties["system.busy_cycles"] = 1
        self.properties["system.core0.fpu_accesses"] = fpu_access
        self.properties["system.core0.ialu_accesses"] = int_alu_access
        self.properties["system.core0.mul_accesses"] = mul_alu_access

        self.name = self.type
        self.key = 'func_unit', self.type, self.tech_node, self.clockrate
        if self.type == "fpu":
            self.mcpat_patterns = ["Floating Point Units"]
        elif self.type == "int_alu":
            self.mcpat_patterns = ["Integer ALUs"]
        else:
            self.mcpat_patterns = ["Complex ALUs"]

    def attr_supported(self):
        return self.datawidth == 32 and self.type in ["fpu", "int_alu", "mul_alu"]

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] == "instruction"


class McPatCache(McPatComponent):

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
        read_access, read_misses, write_access, write_miss = 0, 0, 0, 0
        action_name = self.interface["action_name"]
        if action_name == "read_access":
            read_access = 1
        elif action_name == "read_miss":
            read_access, read_misses = 1, 1
        elif action_name == "write_access":
            write_access = 1
        elif action_name == "write_miss":
            write_access, write_miss = 1, 1

        config_string = "%s, %s, %s, %s, 1, %s, %s, 0" % \
            (size, block_size, associativity, n_banks, data_latency, datawidth)
        buffer_string = "%s, 4, 4, %s" % (mshr_size, write_buffer_size)


        self.properties["system.total_cycles"] = 1
        self.properties["system.busy_cycles"] = 1

        cache_type = self.interface["attributes"]["cache_type"]
        if cache_type == "icache":
            mcpat_path = "system.core0.icache"
            mcpat_config_path = "system.core0.icache.icache_config"
            self.properties[mcpat_config_path] = config_string
            self.properties["%s.buffer_sizes" % mcpat_path] = buffer_string
            self.properties["%s.read_accesses" % mcpat_path] = read_access
            self.properties["%s.read_misses" % mcpat_path] = read_misses
            self.properties["%s.conflicts" % mcpat_path] = 0
        elif cache_type == "dcache":
            mcpat_path = "system.core0.dcache"
            mcpat_config_path = "system.core0.dcache.dcache_config"
            self.properties[mcpat_config_path] = config_string
            self.properties["%s.buffer_sizes" % mcpat_path] = buffer_string
            self.properties["%s.read_accesses" % mcpat_path] = read_access
            self.properties["%s.read_misses" % mcpat_path] = read_misses
            self.properties["%s.write_accesses" % mcpat_path] = write_access
            self.properties["%s.write_misses" % mcpat_path] = write_miss
            self.properties["%s.conflicts" % mcpat_path] = 0
            mcpat_path = "system.L1Directory0"
            mcpat_config_path = "system.L1Directory0.Dir_config"
            self.properties[mcpat_config_path] = config_string
            self.properties["%s.buffer_sizes" % mcpat_path] = buffer_string
            self.properties["%s.read_accesses" % mcpat_path] = read_access
            self.properties["%s.read_misses" % mcpat_path] = read_misses
            self.properties["%s.write_accesses" % mcpat_path] = write_access
            self.properties["%s.write_misses" % mcpat_path] = write_miss
            self.properties["%s.conflicts" % mcpat_path] = 0
            self.properties["%s.clockrate" % mcpat_path] = self.clockrate
            # self.properties["%s.duty_cycle" % mcpat_path] = 1
        else:
            mcpat_path = "system.L20"
            mcpat_config_path = "system.L20.L2_config"
            self.properties[mcpat_config_path] = config_string
            self.properties["%s.buffer_sizes" % mcpat_path] = buffer_string
            self.properties["%s.read_accesses" % mcpat_path] = read_access
            self.properties["%s.read_misses" % mcpat_path] = read_misses
            self.properties["%s.write_accesses" % mcpat_path] = write_access
            self.properties["%s.write_misses" % mcpat_path] = write_miss
            self.properties["%s.conflicts" % mcpat_path] = 0
            self.properties["%s.clockrate" % mcpat_path] = self.clockrate
            mcpat_path = "system.L2Directory0"
            mcpat_config_path = "system.L2Directory0.Dir_config"
            self.properties["%s.buffer_sizes" % mcpat_path] = buffer_string
            self.properties["%s.read_accesses" % mcpat_path] = read_access
            self.properties["%s.read_misses" % mcpat_path] = read_misses
            self.properties["%s.write_accesses" % mcpat_path] = write_access
            self.properties["%s.write_misses" % mcpat_path] = write_miss
            self.properties["%s.conflicts" % mcpat_path] = 0
            self.properties["%s.clockrate" % mcpat_path] = self.clockrate
            # self.properties["%s.duty_cycle" % mcpat_path] = 1


        self.name = cache_type
        self.key = (cache_type, self.interface["action_name"], self.tech_node, self.clockrate,
                    datawidth, size, block_size, associativity, data_latency, mshr_size,
                    write_buffer_size, n_banks)
        if cache_type == "icache":
            self.mcpat_patterns = ["Instruction Cache"]
        elif cache_type == "dcache":
            self.mcpat_patterns = ["Data Cache", "Total First Level Directory"]
        else:
            self.mcpat_patterns = ["\*\*\*\nL2", "Total Second Level Directory"]


    def attr_supported(self):
        return self.interface["attributes"]["cache_type"] in ["icache", "dcache", "l2cache"]

    def action_supported(self):
        cache_type = self.interface["attributes"]["cache_type"]
        if cache_type == "icache":
            return self.interface["action_name"] in ["read_access", "read_miss"]
        elif cache_type in ["dcache", "l2cache"]:
            return self.interface["action_name"] in ["read_access", "read_miss", "write_access", "write_miss"]
        else:
            return False


components = {
    "func_unit": McPatFuncUnit,
    "cache": McPatCache,
}
