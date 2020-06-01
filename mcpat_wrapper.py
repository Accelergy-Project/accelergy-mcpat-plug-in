MCPAT_ACCURACY = 80  # in your metric, please set the accuracy you think McPat's estimations are

#-------------------------------------------------------------------------------
# McPat Version 1.3 wrapper for generating energy estimations of architecture components
#-------------------------------------------------------------------------------
import subprocess, os, csv, glob, tempfile, math, shutil, re
from datetime import datetime

class McPatWrapper:
    """
    an estimation plug-in
    """
    # -------------------------------------------------------------------------------------
    # Interface functions, function name, input arguments, and output have to adhere
    # -------------------------------------------------------------------------------------
    def __init__(self, output_prefix = ''):
        self.estimator_name =  "McPat"
        self.output_prefix = output_prefix
        self.records = {} # enable data reuse

        # primitive classes supported by this estimator
        self.supported_pc = ['fpu_unit', 'cache']

        self.component_to_default_xml_filename = {
            "fpu": 'templates/fpu.xml',
            "icache": 'templates/icache.xml'
        }

        self.component_to_xml_filename = {
            "fpu": 'fpu.xml',
            "icache": "icache.xml"
        }

        self.component_to_stats_regex = {
            "fpu": "(Floating Point Units)(.*\n){5}(.*)",
            "icache": "(Instruction Cache:)(.*\n){5}(.*)"
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
        class_name = interface['class_name']
        attributes = interface['attributes']
        action_name = interface['action_name']
        arguments = interface['arguments']
        if class_name in self.supported_pc:
            attributes_supported_function = class_name + '_attr_supported'
            if getattr(self, attributes_supported_function)(attributes):
                action_supported_function = class_name + '_action_supported'
                accuracy = getattr(self, action_supported_function)(action_name, attributes, arguments)
                if accuracy is not None:
                    return accuracy
        return 0  # if not supported, accuracy is 0

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
        class_name = interface['class_name']
        query_function_name = class_name + '_estimate_energy'
        energy = getattr(self, query_function_name)(interface)
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
        class_name = interface['class_name']
        attributes = interface['attributes']

        if class_name in self.supported_pc:  # McPat supports fpu area estimation
            attributes_supported_function = class_name + '_attr_supported'
            if getattr(self, attributes_supported_function)(attributes):
                return MCPAT_ACCURACY
        return 0  # if not supported, accuracy is 0


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
        class_name = interface['class_name']
        query_function_name = class_name + '_estimate_area'
        area = getattr(self, query_function_name)(interface)
        return area

    def parse_technology(self, technology_string):
        '''
        In the future this could be adapted to accomodate more units and convert
        then to nm as McPat requires for tech_node
        '''
        if 'nm' in technology_string:
            technology_string = technology_string[:-2]  # remove the unit
        return technology_string

    def parse_clockrate(self, clockrate_string):
        '''
        In the future this could be adapted to accomodate more units and convert
        then to mhz as McPat requires for clockrate
        '''
        if 'mhz' in clockrate_string:
            clockrate_string = clockrate_string[:-3]
        return clockrate_string

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

    def construct_entry_key(self, key_descriptor, param_to_val, component_type):
        if component_type == "fpu":
            return self.fpu_unit_construct_entry_key(key_descriptor, param_to_val)
        elif component_type == "icache":
            return self.icache_construct_entry_key(key_descriptor, param_to_val)
        else:
            raise Exception("component type: " + component_type + " not supported")

    def populate_data(self, param_to_val, component_type, action_name=""):
        default_xml_file_name = self.component_to_default_xml_filename[component_type]
        xml_file_name = self.component_to_xml_filename[component_type]
        xml_file_name = self.output_prefix + xml_file_name if self.output_prefix != '' else xml_file_name
        results_file_path = self.mcpat_wrapper(param_to_val, default_xml_file_name, xml_file_name)

        # get energy of fp instruction as this is the only energy estimate of fpu we support
        # for mcpat right now, thus regardless of the input action name this is the energy
        # we fetch right now
        with open(results_file_path) as results_file:
            mcpat_output_string = results_file.read()
            regex_for_stats = self.component_to_stats_regex[component_type]
            results_dict = self.fetch_output_stat_to_value(mcpat_output_string, regex_for_stats)

            area_mm_2 = results_dict["Area"]
            dynamic_watts = results_dict["RuntimeDynamic"]
            energy_pJ = self.calc_pj_from_watts(dynamic_watts, int(param_to_val["CLOCKRATE"]))
            
        if action_name != "":
            entry_key = self.construct_entry_key(action_name, param_to_val, component_type)
            self.records.update({entry_key: energy_pJ})

        # record area entry
        entry_key = self.construct_entry_key('area', param_to_val, component_type)
        self.records.update({entry_key: area_mm_2})
        os.system("rm " + results_file_path)  # all information recorded, no need for saving the file

    def mcpat_wrapper(self, param_to_val, default_xml_file_name, xml_file_path):
        '''
        return the temporary file where the results are located
        xml_file_path included for debugging purposes, can be removed later and a temp
            file used instead
        '''
        # first get the mcpat execution path
        mcpat_exec_path = self.search_for_mcpat_exec_path()

        default_xml_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), default_xml_file_name)
        # create temporary architecture file first
        with open(default_xml_file_path, "r") as file:
            temp_xml = file.read()

        for param_name, value in param_to_val.items():
            temp_xml = re.sub(r"\$" + param_name, value, temp_xml)

        # substitute in the values for the default xml file ie: default_fpu.xml
        with open(xml_file_path, "w") as dest_file:
            dest_file.write(temp_xml)

        # create a temporary output file to redirect terminal output of mcpat
        temp_output, temp_file_path =  tempfile.mkstemp()
        # call mcpat executable to evaluate energy consumption
        # set print level to 5 so we get the fpu energy and area details
        exec_list = [mcpat_exec_path, '-infile', xml_file_path, "-print_level", "5"]
        subprocess.call(exec_list, stdout=temp_output)

        temp_dir = tempfile.gettempdir()
        accelergy_tmp_dir = os.path.join(temp_dir, 'accelergy')
        if os.path.exists(accelergy_tmp_dir):
            if len(os.listdir(accelergy_tmp_dir)) > 50: # clean up the dir if there are more than 50 files
                shutil.rmtree(accelergy_tmp_dir, ignore_errors=True)
                os.mkdir(accelergy_tmp_dir)
        else:
            os.mkdir(accelergy_tmp_dir)
        shutil.copy(xml_file_path,
                    os.path.join(temp_dir, 'accelergy/'+ xml_file_path + '_' + datetime.now().strftime("%m_%d_%H_%M_%S")))
        os.remove(xml_file_path)
        return temp_file_path

    def fetch_output_stat_to_value(self, mcpat_output_string, regex_for_stats):
        output_match_obj = re.search(regex_for_stats, mcpat_output_string)
        output_string = output_match_obj.group(0)
        output_string = re.sub(" ", "", output_string)
        output_split_lines = output_string.split("\n")

        results_dict = {}
        for line in output_split_lines:
            if "=" in line:
                split_line = line.split("=")
                key = split_line[0]
                # get value with all units following it removed
                value = re.match("[.0-9]*", split_line[1]).group(0)
                results_dict[key] = float(value)
        return results_dict

    def calc_pj_from_watts(self, watts, clockrate_mhz):
        num_cycles = 1.0 # value I set in template file for total number of cycles
        execution_time = num_cycles / (float(clockrate_mhz) * 10**6) 
        # Must multiply watts by execution time as McPat divides by it to get watts
        energy_joules = watts * execution_time
        energy_pj = energy_joules * 10**12
        return energy_pj

    # ----------------- FPU related ---------------------------
    def fpu_unit_construct_param_to_val(self, attributes):
        param_to_val = {
            "TECH_NODE": self.parse_technology(str(attributes['technology'])),
            "CLOCKRATE": self.parse_clockrate(str(attributes['clockrate']))
        }
        return param_to_val

    def fpu_unit_construct_entry_key(self, key_descriptor, param_to_val):
        entry_key = ('fpu_unit', key_descriptor, param_to_val["TECH_NODE"], param_to_val["CLOCKRATE"])
        return entry_key

    def fpu_unit_estimate_area(self, interface):
        attributes = interface['attributes']
        param_to_val = self.fpu_unit_construct_param_to_val(attributes)

        desired_entry_key = self.fpu_unit_construct_entry_key('area', param_to_val)

        if desired_entry_key not in self.records:
            print('Info: McPat plug-in... Querying McPat for request:\n', interface)
            self.populate_data(param_to_val, "fpu")
        area = self.records[desired_entry_key]
        return area # output area is in mm^2

    def fpu_unit_estimate_energy(self, interface):
        action_name = interface['action_name']
        attributes = interface['attributes']
        param_to_val = self.fpu_unit_construct_param_to_val(attributes)
        desired_action_name = interface['action_name']

        desired_entry_key = self.fpu_unit_construct_entry_key(desired_action_name, param_to_val)

        if desired_entry_key not in self.records:
            print('Info: McPat plug-in... Querying McPat for request:\n', interface)
            self.populate_data(param_to_val, "fpu", desired_action_name)
        energy = self.records[desired_entry_key]
        return energy  # output energy is pJ

    def fpu_unit_attr_supported(self, attributes):
        return True

    def fpu_unit_action_supported(self, action_name, attributes, arguments):
        supported_actions = ['fp_instruction']
        if action_name in supported_actions:
            return MCPAT_ACCURACY
        else:
            return None

    # ----------------- General cache related ---------------------------
    # making a general cache related section so that L2 caches can fit in here
    # if/when support for them works again in McPat
    def cache_estimate_area(self, interface):
        attributes = interface['attributes']
        cache_type = attributes["cache_type"]
        if cache_type == "icache":
            return self.icache_estimate_area(interface)
        else:
            raise Exception("cache_type: " + cache_type + " not supported")
        

    def cache_estimate_energy(self, interface):
        attributes = interface['attributes']
        cache_type = attributes["cache_type"]
        if cache_type == "icache":
            return self.icache_estimate_energy(interface)
        else:
            raise Exception("cache_type: " + cache_type + " not supported")

    def cache_attr_supported(self, attributes):
        supported_cache_types = ["icache"] # TODO "dcache" will be added too
        if attributes["cache_type"] in supported_cache_types:
            return True
        return False

    def cache_action_supported(self, action_name, attributes, arguments):
        cache_type = attributes["cache_type"]
        if cache_type == "icache":
            return self.icache_action_supported(action_name, arguments)
        else:
            raise Exception("cache_type: " + cache_type + " not supported")

    # -----------------  icache related ---------------------------
    def icache_construct_param_to_val(self, attributes, action_name=""):
        param_to_val = {
            "TECH_NODE": self.parse_technology(str(attributes['technology'])),
            "CLOCKRATE": self.parse_clockrate(str(attributes['clockrate'])),
            # size in bytes, potentially add parse support for units later
            "SIZE": str(attributes["size"]),
            # also in bytes, add support for other units later
            "BLOCK_WIDTH": str(attributes["block_size"]),
            "ASSOC": str(attributes["associativity"]),
            # need to add these add ints and then convert back to strings
            "LATENCY": str(int(attributes["hit_latency"]) + int(attributes["response_latency"])),
            # max number of outstanding requests
            "MSHRS": str(attributes["mshrs"]),
            "READ_ACCESSES": "0",
            "READ_MISSES": "0",
        }
        if action_name == "read_access":
            param_to_val["READ_ACCESSES"] = "1"
        elif action_name == "read_miss":
            param_to_val["READ_MISSES"] = "1"
        return param_to_val

    def icache_construct_entry_key(self, key_descriptor, param_to_val):
        entry_key = ('icache', key_descriptor, param_to_val["TECH_NODE"],
                      param_to_val["CLOCKRATE"], param_to_val["SIZE"],
                      param_to_val["BLOCK_WIDTH"], param_to_val["ASSOC"],
                      param_to_val["LATENCY"], param_to_val["MSHRS"]
                    )
        return entry_key

    def icache_estimate_area(self, interface):
        attributes = interface['attributes']
        param_to_val = self.icache_construct_param_to_val(attributes)

        desired_entry_key = self.icache_construct_entry_key('area', param_to_val)

        if desired_entry_key not in self.records:
            print('Info: McPat plug-in... Querying McPat for request:\n', interface)
            self.populate_data(param_to_val, "icache")
        area = self.records[desired_entry_key]
        return area # output area is in mm^2

    def icache_estimate_energy(self, interface):
        action_name = interface['action_name']
        attributes = interface['attributes']
        param_to_val = self.icache_construct_param_to_val(attributes, action_name)
        desired_action_name = interface['action_name']

        desired_entry_key = self.icache_construct_entry_key(desired_action_name, param_to_val)

        if desired_entry_key not in self.records:
            print('Info: McPat plug-in... Querying McPat for request:\n', interface)
            self.populate_data(param_to_val, "icache", desired_action_name)
        energy = self.records[desired_entry_key]
        return energy  # output energy is pJ


    def icache_action_supported(self, action_name, arguments):
        supported_actions = ['read_access', 'read_miss']
        if action_name in supported_actions:
            return MCPAT_ACCURACY
        else:
            return None

