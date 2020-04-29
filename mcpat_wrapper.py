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
        # example primitive classes supported by this estimator
        self.supported_pc = ['fpu_unit']
        self.records = {} # enable data reuse

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
                accuracy = getattr(self, action_supported_function)(action_name, arguments)
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

    # ----------------- FPU related ---------------------------
    def fpu_unit_populate_data(self, interface):
        action_name = interface['action_name']
        attributes = interface['attributes']
        tech_node = str(attributes['technology'])
        if 'nm' in tech_node:
            tech_node = tech_node[:-2]  # remove the unit
        clockrate_mhz = str(attributes['clockrate'])
        if 'mhz' in clockrate_mhz:
            clockrate_mhz = clockrate_mhz[:-3]
        print('Info: McPat plug-in... Querying McPat for request:\n', interface)
        curr_dir = os.path.abspath(os.getcwd())
        mcpat_exec_path = self.search_for_mcpat_exec_path()

        xml_file_name = self.output_prefix + 'fpu.xml' if self.output_prefix is not '' else 'fpu.xml'
        results_file_path = self.mcpat_wrapper_for_fpu(mcpat_exec_path, tech_node, clockrate_mhz, xml_file_name)

        # get energy of fp instruction as this is the only energy estimate of fpu we support
        # for mcpat right now, thus regardless of the input action name this is the energy
        # we fetch right now
        with open(results_file_path) as results_file:
            result_text = results_file.read()
            # result = re.match("(Floating Point Units)(.*\n){6}", result_text)
            fpu_output_match_obj = re.search("(Floating Point Units)(.*\n){5}(.*)", result_text)
            fpu_output_string = fpu_output_match_obj.group(0)
            fpu_output_string = re.sub(" ", "", fpu_output_string)
            fpu_output_split_lines = fpu_output_string.split("\n")

            results_dict = {}
            for line in fpu_output_split_lines:
                if "=" in line:
                    split_line = line.split("=")
                    key = split_line[0]
                    # get value with all units following it removed
                    value = re.match("[.0-9]*", split_line[1]).group(0)
                    results_dict[key] = float(value)
            area_mm_2 = results_dict["Area"]
            dynamic_watts = results_dict["RuntimeDynamic"]
            num_cycles = 1.0 # value I set in template file for total number of cycles
            # Execution time calculation from McPat
            execution_time = num_cycles / (float(clockrate_mhz) * 10**6) 
            # Must multiply by execution time as McPat divides by it to get Watts
            energy_joules = dynamic_watts * execution_time
            energy_pJ = energy_joules * 10**12 # this is to get pJ
            
        # record energy entry
        entry_key = ('fpu_unit', action_name, tech_node, clockrate_mhz)
        self.records.update({entry_key: energy_pJ})

        # record area entry
        entry_key = ('fpu_unit', 'area', tech_node, clockrate_mhz)
        self.records.update({entry_key: area_mm_2})
        os.system("rm " + results_file_path)  # all information recorded, no need for saving the file

    def fpu_unit_estimate_area(self, interface):
        attributes = interface['attributes']
        tech_node = str(attributes['technology'])
        if 'nm' in tech_node:
            tech_node = tech_node[:-2]  # remove the unit
        clockrate_mhz = str(attributes['clockrate'])
        if 'mhz' in clockrate_mhz:
            clockrate_mhz = clockrate_mhz[:-3]
        desired_entry_key = ('fpu_unit', 'area', tech_node, clockrate_mhz)
        if desired_entry_key not in self.records:
            self.fpu_unit_populate_data(interface)
        area = self.records[desired_entry_key]
        return area # output area is in mm^2

    def fpu_unit_estimate_energy(self, interface):
        action_name = interface['action_name']
        attributes = interface['attributes']
        tech_node = str(attributes['technology'])
        if 'nm' in tech_node:
            tech_node = tech_node[:-2]  # remove the unit
        clockrate_mhz = str(attributes['clockrate'])
        if 'mhz' in clockrate_mhz:
            clockrate_mhz = clockrate_mhz[:-3]
        desired_action_name = interface['action_name']
        desired_action_named_entry_key = ('fpu_unit', desired_action_name, tech_node, clockrate_mhz)
        if desired_action_named_entry_key not in self.records:
            self.fpu_unit_populate_data(interface)
        energy = self.records[desired_action_named_entry_key]
        return energy  # output energy is pJ

    def fpu_unit_attr_supported(self, attributes):
        return True

    def fpu_unit_action_supported(self, action_name, arguments):
        supported_actions = ['fp_instruction']
        if action_name in supported_actions:
            return 95
        else:
            return None

    def mcpat_wrapper_for_fpu(self, mcpat_exec_path, tech_node, clockrate_mhz, xml_file_path):
        '''
        return the temporary file where the results are located
        '''
        default_xml_file_name = 'default_fpu.xml'
        default_xml_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), default_xml_file_name)
        # create temporary architecture file first
        with open(default_xml_file_path, "r") as file:
            fpu_xml = file.read()

        fpu_xml = re.sub("TECH_NODE", str(tech_node), fpu_xml)
        fpu_xml = re.sub("CLOCKRATE", str(clockrate_mhz), fpu_xml)

        with open(xml_file_path, "w") as dest_file:
            dest_file.write(fpu_xml)

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

