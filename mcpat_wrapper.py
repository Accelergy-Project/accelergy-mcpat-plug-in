import os
import re
import copy
import json
import subprocess
import time
import xml.etree.ElementTree as ET

# -------------------------------------------------------------------------------
# McPat Version 1.3 wrapper for generating energy estimations of architecture components
# -------------------------------------------------------------------------------

MCPAT_ACCURACY = 80  # in your metric, please set the accuracy you think McPat's estimations are

MUL_FACTOR = 1000000  # averaging factor for McPAT
CACHE_TIMEOUT = 30    # cache timeout in days

class McPatWrapper:
    """
    an estimation plug-in
    """

    # -------------------------------------------------------------------------------------
    # Interface functions, function name, input arguments, and output have to adhere
    # -------------------------------------------------------------------------------------
    def __init__(self, clean_output_files=True, verbose=True):
        self.estimator_name = "McPat"
        self.exec_path = search_for_mcpat_exec_path()
        self.clean_output_files = clean_output_files
        self.verbose = verbose
        self.cache = {}
        self.cache_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".cache")
        self.load_cache()  # enable data caching across invocations

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

        identifier = interface["class_name"]
        if "type" in interface["attributes"]:
            identifier += " " + interface["attributes"]["type"]
        identifier += " " + interface["action_name"]

        if key in self.cache:
            if self.verbose:
                print("Info: accelergy-mcpat-plugin [%s] cached=1 energy=%fpJ area=%fmm^2" % (identifier, self.cache[key][0], self.cache[key][1]))
            return self.cache[key][0]
        else:
            energy, area = self.query_mcpat(component)
            self.write_cache(key, energy, area)
            if self.verbose:
                print("Info: accelergy-mcpat-plugin [%s] cached=0 energy=%fpJ area=%fmm^2" % (identifier, energy, area))
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
            self.write_cache(key, energy, area)
            return area

    def load_cache(self):
        if os.path.exists(self.cache_file):
            entries = []
            with open(self.cache_file, "r") as file:
                for line in file.readlines():
                    entry = json.loads(line)
                    entry_time = entry[3]
                    current_time = time.time()
                    timeout = CACHE_TIMEOUT * 86400
                    if current_time > entry_time > current_time - timeout:
                        entries.append(entry)
            with open(self.cache_file, "w") as file:
                for entry in entries:
                    json.dump(entry, file)
                    file.write("\n")
                    self.cache[tuple(entry[0])] = (entry[1], entry[2])

    def write_cache(self, key, energy, area):
        self.cache[key] = (energy, area)
        with open(self.cache_file, "a") as file:
            json.dump([key, energy, area, time.time()], file)
            file.write("\n")

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
                pattern = re.compile(mcpat_pattern + r"[\w\W]*?Area = ([^\s]*)[\w\W]*?Runtime Dynamic = ([^\s]*)")
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
        "system.Embedded": 0,
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
        self.properties["system.total_cycles"] = MUL_FACTOR
        self.properties["system.core0.total_cycles"] = MUL_FACTOR
        self.properties["system.busy_cycles"] = MUL_FACTOR
        self.properties["system.core0.busy_cycles"] = MUL_FACTOR

        datawidth = interface["attributes"]["datawidth"]
        self.properties["system.machine_bits"] = datawidth
        self.datawidth = datawidth

        device_type = interface["attributes"]["device_type"]
        if device_type == "hp":
            device_type_code = 0
        if device_type == "lstp":
            device_type_code = 1
        if device_type == "lop":
            device_type_code = 2
        self.properties["system.device_type"] = device_type_code
        self.device_type = device_type

        self.global_attrs = (tech_node, clockrate, datawidth, device_type)


class McPatFuncUnit(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        self.type = interface["attributes"]["type"]
        action_name = interface["action_name"]
        if action_name == "access":
            action_count = MUL_FACTOR
        elif action_name == "idle":
            action_count = 0

        self.name = "func_unit"
        self.key = ("func_unit", self.type, action_name, *self.global_attrs)
        if self.type == "fpu":
            self.properties["system.core0.fpu_accesses"] = action_count
            self.mcpat_patterns = ["Floating Point Units"]
        elif self.type == "int_alu":
            self.properties["system.core0.ialu_accesses"] = action_count
            self.mcpat_patterns = ["Integer ALUs"]
        else:
            self.properties["system.core0.mul_accesses"] = action_count
            self.mcpat_patterns = ["Complex ALUs"]

    def attr_supported(self):
        return self.type in ["fpu", "int_alu", "mul_alu"]

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] in ["access", "idle"]


class McPatXBar(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        horizontal_nodes = interface["attributes"]["horizontal_nodes"]
        vertical_nodes = interface["attributes"]["vertical_nodes"]
        throughput = interface["attributes"]["link_throughput"]
        latency = interface["attributes"]["link_latency"]
        flit_bits = interface["attributes"]["flit_bytes"] * 8

        self.properties["system.noc0.clockrate"] = self.clockrate
        self.properties["system.noc0.horizontal_nodes"] = horizontal_nodes
        self.properties["system.noc0.vertical_nodes"] = vertical_nodes
        self.properties["system.noc0.link_throughput"] = throughput
        self.properties["system.noc0.link_latency"] = latency
        self.properties["system.noc0.flit_bits"] = flit_bits
        self.properties["system.noc0.total_accesses"] = MUL_FACTOR

        self.name = "xbar"
        self.key = ("xbar", *self.global_attrs, horizontal_nodes,
                    vertical_nodes, throughput, latency, flit_bits)
        self.mcpat_patterns = ["Total NoCs"]

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] == "access"


class McPatCache(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        size = interface["attributes"]["size"]                            # size in bytes
        block_size = interface["attributes"]["block_size"]                # block size in bytes
        associativity = interface["attributes"]["associativity"]          # cache associativity
        data_latency = interface["attributes"]["data_latency"]            # data latency in cycles
        mshr_size = interface["attributes"]["mshr_size"]                  # maximum outstanding requests
        write_buffer_size = interface["attributes"]["write_buffer_size"]  # write buffer size
        n_banks = interface["attributes"]["n_banks"]                      # number of cache banks

        action_name = interface["action_name"]
        read_access, read_misses, write_access, write_miss = 0, 0, 0, 0
        if action_name == "read_hit":
            read_access = MUL_FACTOR
        elif action_name == "read_miss":
            read_access, read_misses = MUL_FACTOR, MUL_FACTOR
        elif action_name == "write_hit":
            write_access = MUL_FACTOR
        elif action_name == "write_miss":
            write_access, write_miss = MUL_FACTOR, MUL_FACTOR

        cache_type = interface["attributes"]["cache_type"]
        if cache_type == "icache":
            mcpat_path = "system.core0.icache"
            mcpat_config_path = "system.core0.icache.icache_config"
            self.mcpat_patterns = ["Instruction Cache"]
        elif cache_type == "dcache":
            mcpat_path = "system.core0.dcache"
            mcpat_config_path = "system.core0.dcache.dcache_config"
            self.properties["%s.write_accesses" % mcpat_path] = write_access
            self.properties["%s.write_misses" % mcpat_path] = write_miss
            self.mcpat_patterns = ["Data Cache"]
        else:
            mcpat_path = "system.L20"
            mcpat_config_path = "system.L20.L2_config"
            self.properties["%s.write_accesses" % mcpat_path] = write_access
            self.properties["%s.write_misses" % mcpat_path] = write_miss
            self.properties["%s.clockrate" % mcpat_path] = self.clockrate
            self.mcpat_patterns = ["L2\n"]

        config_string = "%s, %s, %s, %s, 1, %s, %s, 0" % \
                        (size, block_size, associativity, n_banks, data_latency, self.datawidth)
        buffer_string = "%s, 4, 4, %s" % (mshr_size, write_buffer_size)

        self.properties[mcpat_config_path] = config_string
        self.properties["%s.buffer_sizes" % mcpat_path] = buffer_string
        self.properties["%s.read_accesses" % mcpat_path] = read_access
        self.properties["%s.read_misses" % mcpat_path] = read_misses
        self.properties["%s.conflicts" % mcpat_path] = 0

        self.name = "cache"
        self.key = ("cache", cache_type, action_name, *self.global_attrs, size, block_size,
                    associativity, data_latency, mshr_size, write_buffer_size, n_banks)

    def attr_supported(self):
        return self.interface["attributes"]["cache_type"] in ["icache", "dcache", "l2cache"]

    def action_supported(self):
        cache_type = self.interface["attributes"]["cache_type"]
        if cache_type == "icache":
            return self.interface["action_name"] in ["read_hit", "read_miss"]
        elif cache_type in ["dcache", "l2cache"]:
            return self.interface["action_name"] in ["read_hit", "read_miss", "write_hit", "write_miss"]
        else:
            return False


class McPatTournamentBP(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        local_entries = interface["attributes"]["local_pred_entries"]
        local_bits = interface["attributes"]["local_pred_bits"]
        global_entries = interface["attributes"]["global_pred_entries"]
        global_bits = interface["attributes"]["global_pred_bits"]
        choice_entries = interface["attributes"]["choice_pred_entries"]
        choice_bits = interface["attributes"]["choice_pred_bits"]

        base = "system.core0.PBT."
        self.properties[base + "local_predictor_size"] = "%d, %d" % (local_bits, local_bits)
        self.properties[base + "local_predictor_entries"] = local_entries
        self.properties[base + "global_predictor_bits"] = global_bits
        self.properties[base + "global_predictor_entries"] = global_entries
        self.properties[base + "chooser_predictor_bits"] = choice_bits
        self.properties[base + "chooser_predictor_entries"] = choice_entries

        action_name = interface["action_name"]
        if action_name == "hit":
            bp_access, bp_miss = MUL_FACTOR, 0
        elif action_name == "miss":
            bp_access, bp_miss = MUL_FACTOR, MUL_FACTOR

        self.properties["system.core0.branch_instructions"] = bp_access
        self.properties["system.core0.branch_mispredictions"] = bp_miss

        self.name = "tournament_bp"
        self.key = ("tournament_bp", action_name, *self.global_attrs, local_entries,
                    local_bits, global_entries, global_bits, choice_entries, choice_bits)
        self.mcpat_patterns = ["Branch Predictor"]

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] in ["hit", "miss"]


class McPatBTB(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        entries = interface["attributes"]["entries"]
        block_width = interface["attributes"]["block_width"]
        associativity = interface["attributes"]["associativity"]
        banks = interface["attributes"]["banks"]
        action_name = interface["action_name"]
        if action_name == "read":
            read, write = MUL_FACTOR, 0
        elif action_name == "write":
            read, write = 0, MUL_FACTOR

        config_string = "%s, %s, %s, %s, 1, 1" % (entries, block_width, associativity, banks)

        self.properties["system.core0.BTB.BTB_config"] = config_string
        self.properties["system.core0.BTB.read_accesses"] = read
        self.properties["system.core0.BTB.write_accesses"] = write
        self.mcpat_patterns = ["Branch Target Buffer"]

        self.name = "btb"
        self.key = ("btb", action_name, *self.global_attrs, entries, block_width, associativity, banks)

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] in ["read", "write"]


class McPatCpuRegfile(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        phys_size = interface["attributes"]["phys_size"]
        issue_width = interface["attributes"]["issue_width"]
        action_name = interface["action_name"]
        if action_name == "read":
            read, write = MUL_FACTOR, 0
        elif action_name == "write":
            read, write = 0, MUL_FACTOR

        regfile_type = interface["attributes"]["type"]
        if regfile_type == "int":
            self.properties["system.core0.phy_Regs_IRF_size"] = phys_size
            self.properties["system.core0.peak_issue_width"] = issue_width
            self.properties["system.core0.int_regfile_reads"] = read
            self.properties["system.core0.int_regfile_writes"] = write
            self.mcpat_patterns = ["Integer RF"]
        elif regfile_type == "fp":
            self.properties["system.core0.phy_Regs_FRF_size"] = phys_size
            self.properties["system.core0.issue_width"] = issue_width
            self.properties["system.core0.float_regfile_reads"] = read
            self.properties["system.core0.float_regfile_writes"] = write
            self.mcpat_patterns = ["Floating Point RF"]

        self.name = "cpu_regfile"
        self.key = ("cpu_regfile", action_name, regfile_type, *self.global_attrs, phys_size, issue_width)

    def attr_supported(self):
        return self.interface["attributes"]["type"] in ["int", "fp"]

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] in ["read", "write"]


class McPatTlb(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        entries = interface["attributes"]["entries"]
        action_name = interface["action_name"]
        if action_name == "hit":
            access, miss = MUL_FACTOR, 0
        elif action_name == "miss":
            access, miss = MUL_FACTOR, MUL_FACTOR

        self.properties["system.core0.itlb.number_entries"] = entries
        self.properties["system.core0.itlb.total_accesses"] = access
        self.properties["system.core0.itlb.total_misses"] = miss

        self.name = "tlb"
        self.key = ("tlb", action_name, *self.global_attrs, entries)
        self.mcpat_patterns = ["Itlb"]

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] in ["hit", "miss"]


class McPatRenamingUnit(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        decode_width = interface["attributes"]["decode_width"]
        commit_width = interface["attributes"]["commit_width"]
        phys_irf_size = interface["attributes"]["phys_irf_size"]
        phys_frf_size = interface["attributes"]["phys_frf_size"]
        action_name = interface["action_name"]
        if action_name == "read":
            read, write = MUL_FACTOR, 0
        elif action_name == "write":
            read, write = 0, MUL_FACTOR

        self.properties["system.core0.decode_width"] = decode_width
        self.properties["system.core0.commit_width"] = decode_width
        self.properties["system.core0.phy_Regs_IRF_size"] = phys_irf_size
        self.properties["system.core0.phy_Regs_FRF_size"] = phys_frf_size
        self.properties["system.core0.rename_reads"] = read
        self.properties["system.core0.rename_writes"] = write
        self.properties["system.core0.fp_rename_reads"] = 0
        self.properties["system.core0.fp_rename_writes"] = 0
        self.mcpat_patterns = ["Renaming Unit"]

        self.name = "renaming_unit"
        self.key = ("renaming_unit", action_name, *self.global_attrs, decode_width, commit_width, phys_irf_size, phys_frf_size)

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] in ["read", "write"]


class McPatReorderBuffer(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        entries = interface["attributes"]["entries"]
        action_name = interface["action_name"]
        if action_name == "read":
            read, write = MUL_FACTOR, 0
        elif action_name == "write":
            read, write = 0, MUL_FACTOR

        self.properties["system.core0.ROB_size"] = entries
        self.properties["system.core0.ROB_reads"] = read
        self.properties["system.core0.ROB_writes"] = write
        self.mcpat_patterns = ["ROB"]

        self.name = "reorder_buffer"
        self.key = ("reorder_buffer", action_name, *self.global_attrs, entries)

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] in ["read", "write"]


class McPatLoadStoreQueue(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        entries = interface["attributes"]["entries"]
        ports = interface["attributes"]["ports"]
        queue_type = interface["attributes"]["type"]
        action_name = interface["action_name"]

        if action_name == "load":
            load_count, store_count = MUL_FACTOR, 0
        elif action_name == "store":
            load_count, store_count = 0, MUL_FACTOR

        if queue_type == "load":
            self.properties["system.core0.load_buffer_size"] = entries
            self.mcpat_patterns = ["LoadQ"]
        elif queue_type == "store":
            self.properties["system.core0.store_buffer_size"] = entries
            self.mcpat_patterns = ["StoreQ"]
        self.properties["system.core0.memory_ports"] = ports
        self.properties["system.core0.store_instructions"] = load_count
        self.properties["system.core0.load_instructions"] = store_count

        self.name = "load_store_queue"
        self.key = ("load_store_queue", *self.global_attrs, entries, ports, queue_type)

    def attr_supported(self):
        return self.interface["attributes"]["type"] in ["load", "store"]

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] in ["load", "store"]


class McPatFetchBuffer(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        entries = interface["attributes"]["entries"]

        self.properties["system.core0.instruction_buffer_size"] = entries
        self.properties["system.core0.total_instructions"] = MUL_FACTOR
        self.mcpat_patterns = ["Instruction Buffer"]

        self.name = "fetch_buffer"
        self.key = ("fetch_buffer", *self.global_attrs, entries)

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] == "access"


class McPatDecoder(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        width = interface["attributes"]["width"]

        self.properties["system.core0.decode_width"] = width
        self.properties["system.core0.total_instructions"] = MUL_FACTOR
        self.mcpat_patterns = ["Instruction Decoder"]

        self.name = "decoder"
        self.key = ("decoder", *self.global_attrs, width)

    def attr_supported(self):
        return True

    def action_supported(self):
        return self.interface["action_name"] == "access"


class McPatInstQueue(McPatComponent):

    def __init__(self, interface):
        super().__init__(interface)
        entries = interface["attributes"]["entries"]
        issue_width = interface["attributes"]["issue_width"]
        action_name = interface["action_name"]
        if action_name == "read":
            read, write, wakeup = MUL_FACTOR, 0, 0
        elif action_name == "write":
            read, write, wakeup = 0, MUL_FACTOR, 0
        elif action_name == "wakeup":
            read, write, wakeup = 0, 0, MUL_FACTOR

        queue_type = interface["attributes"]["type"]
        if queue_type == "int":
            self.properties["system.core0.instruction_window_size"] = entries
            self.properties["system.core0.inst_window_reads"] = read
            self.properties["system.core0.inst_window_writes"] = write
            self.properties["system.core0.inst_window_wakeup_accesses"] = wakeup
            self.mcpat_patterns = ["   Instruction Window"]
        elif queue_type == "fp":
            self.properties["system.core0.fp_instruction_window_size"] = entries
            self.properties["system.core0.fp_inst_window_reads"] = read
            self.properties["system.core0.fp_inst_window_writes"] = write
            self.properties["system.core0.fp_inst_window_wakeup_accesses"] = wakeup
            self.mcpat_patterns = ["FP Instruction Window"]
        self.properties["system.core0.peak_issue_width"] = issue_width

        self.name = "inst_queue"
        self.key = ("inst_queue", queue_type, action_name, *self.global_attrs, entries, issue_width)

    def attr_supported(self):
        return self.interface["attributes"]["type"] in ["int", "fp"]

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] in ["read", "write", "wakeup"]


components = {
    "func_unit": McPatFuncUnit,
    "xbar": McPatXBar,
    "cache": McPatCache,
    "tournament_bp": McPatTournamentBP,
    "btb": McPatBTB,
    "cpu_regfile": McPatCpuRegfile,
    "tlb": McPatTlb,
    "renaming_unit": McPatRenamingUnit,
    "reorder_buffer": McPatReorderBuffer,
    "load_store_queue": McPatLoadStoreQueue,
    "fetch_buffer": McPatFetchBuffer,
    "decoder": McPatDecoder,
    "inst_queue": McPatInstQueue,
}
