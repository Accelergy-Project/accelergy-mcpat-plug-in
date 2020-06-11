from collections import OrderedDict
from mcpat_wrapper import *

wrapper = McPatWrapper(clean_output_files=False)
print(wrapper.exec_path, "\n")

def test(interface):
    print("action supported ", wrapper.primitive_action_supported(interface))
    print("action energy    ", wrapper.estimate_energy(interface), "pJ")
    print("area supported   ", wrapper.primitive_area_supported(interface))
    print("area             ", wrapper.estimate_area(interface), "mm^2\n")


# fpu fpu_instruction
print("fpu fpu_instruction")
test({'class_name': 'fpu_unit',
      'attributes': OrderedDict([
          ('technology', '45nm'), ('clockrate', 1000), ('datawidth', 32), ('exponent', 8), ('mantissa', 24)
      ]),
      'action_name': 'fp_instruction', 'arguments': None})

# icache read_access
print("icache read_access")
test({'class_name': 'cache',
      'attributes': {
          'replacement_policy': 'lrurp', 'associativity': 2, 'tag_size': 64, 'block_size': 64,
          'write_buffers': 8, 'size': 16384, 'mshrs': 4, 'response_latency': 2, 'technology': '45nm',
          'clockrate': 1000, 'cache_type': 'icache', 'datawidth': 32, 'vdd': 1.0,
          'number_hardware_threads': 1, 'hit_latency': 0, 'resp_latency': 0, 'n_rd_ports': 0,
          'n_wr_ports': 0, 'n_rdwr_ports': 1, 'n_banks': 1
      },
      'action_name': 'read_access', 'arguments': None})

# icache read_miss
print("icache read_miss")
test({'class_name': 'cache',
      'attributes': {
          'replacement_policy': 'lrurp', 'associativity': 2, 'tag_size': 64, 'block_size': 64,
          'write_buffers': 8, 'size': 16384, 'mshrs': 4, 'response_latency': 2, 'technology': '45nm',
          'clockrate': 1000, 'cache_type': 'icache', 'datawidth': 32, 'vdd': 1.0,
          'number_hardware_threads': 1, 'hit_latency': 0, 'resp_latency': 0, 'n_rd_ports': 0,
          'n_wr_ports': 0, 'n_rdwr_ports': 1, 'n_banks': 1
      },
      'action_name': 'read_miss', 'arguments': None})
