from collections import OrderedDict
from mcpat_wrapper import *

wrapper = McPatWrapper(clean_output_files=False)
print(wrapper.exec_path, "\n")

def test(interface):
    print("action supported ", wrapper.primitive_action_supported(interface))
    print("action energy    ", wrapper.estimate_energy(interface), "pJ")
    print("area supported   ", wrapper.primitive_area_supported(interface))
    print("area             ", wrapper.estimate_area(interface), "mm^2\n")


# # fpu fpu_instruction
# print("fpu fpu_instruction")
# test({'class_name': 'fpu_unit',
#       'attributes': OrderedDict([
#           ('technology', '45nm'), ('clockrate', 1000), ('datawidth', 32), ('exponent', 8), ('mantissa', 24)
#       ]),
#       'action_name': 'fp_instruction', 'arguments': None})

print("icache read_access")
test({
   "class_name":"cache",
   "attributes":{
      "n_rd_ports":1,
      "n_wr_ports":1,
      "n_rdwr_ports":1,
      "n_banks":4,
      "cache_type":"icache",
      "size":16384,
      "associativity":2,
      "data_latency":2,
      "block_size":64,
      "mshr_size":4,
      "tag_size":64,
      "write_buffer_size":8,
      "technology":"45nm",
      "datawidth":32,
      "clockrate":999
   },
   "action_name":"read_access",
   "arguments":"None"
})

print("icache read_miss")
test({
   "class_name":"cache",
   "attributes":{
      "n_rd_ports":1,
      "n_wr_ports":1,
      "n_rdwr_ports":1,
      "n_banks":4,
      "cache_type":"icache",
      "size":16384,
      "associativity":2,
      "data_latency":2,
      "block_size":64,
      "mshr_size":4,
      "tag_size":64,
      "write_buffer_size":8,
      "technology":"45nm",
      "datawidth":32,
      "clockrate":999
   },
   "action_name":"read_miss",
   "arguments":"None"
})

