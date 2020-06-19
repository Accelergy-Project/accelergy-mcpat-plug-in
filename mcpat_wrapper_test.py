from collections import OrderedDict
from mcpat_wrapper import *

wrapper = McPatWrapper(clean_output_files=False)
print(wrapper.exec_path, "\n")


def test(interface):
    print("action supported ", wrapper.primitive_action_supported(interface))
    print("action energy    ", wrapper.estimate_energy(interface), "pJ")
    print("area supported   ", wrapper.primitive_area_supported(interface))
    print("area             ", wrapper.estimate_area(interface), "mm^2\n")


# icache
req = {
   "class_name":"cache",
   "attributes":{
      "n_rd_ports":1,
      "n_wr_ports":1,
      "n_rdwr_ports":1,
      "n_banks":1,
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
}
print("icache read_access")
test(req)

req["action_name"] = "read_miss"
print("icache read_miss")
test(req)


# dcache
req = {
   "class_name":"cache",
   "attributes":{
      "n_rd_ports":1,
      "n_wr_ports":1,
      "n_rdwr_ports":1,
      "n_banks":1,
      "cache_type":"dcache",
      "size":65536,
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
}
print("dcache read_access")
test(req)

req["action_name"] = "read_miss"
print("dcache read_miss")
test(req)

req["action_name"] = "write_access"
print("dcache write_access")
test(req)

req["action_name"] = "write_miss"
print("dcache write_miss")
test(req)


# l2cache
req = {
   "class_name":"cache",
   "attributes":{
      "n_rd_ports":1,
      "n_wr_ports":1,
      "n_rdwr_ports":1,
      "n_banks":4,
      "cache_type":"l2cache",
      "size":262144,
      "associativity":8,
      "data_latency":20,
      "block_size":64,
      "mshr_size":20,
      "tag_size":64,
      "write_buffer_size":8,
      "technology":"45nm",
      "datawidth":32,
      "clockrate":999
   },
   "action_name":"read_access",
   "arguments":"None"
}
print("l2cache read_access")
test(req)

req["action_name"] = "read_miss"
print("l2cache read_miss")
test(req)

req["action_name"] = "write_access"
print("l2cache write_access")
test(req)

req["action_name"] = "write_miss"
print("l2cache write_miss")
test(req)

# func units
req = {
    "class_name": "func_unit",
    "attributes":{
        "technology":"45nm",
        "clockrate":1000,
        "datawidth":32,
        "type":"fpu"
    },
    "action_name":"instruction",
    "arguments":"None"
}
print("fpu instruction")
test(req)

req["attributes"]["type"] = "int_alu"
print("int_alu instruction")
test(req)

req["attributes"]["type"] = "mul_alu"
print("mul_alu instruction")
test(req)


# xbar
req = {
    "class_name": "xbar",
    "attributes":{
        "technology":"45nm",
        "clockrate":1000,
        "datawidth":32,
        "horizontal_nodes":1,
        "vertical_nodes": 1,
        "link_throughput": 1,
        "link_latency": 2,
        "flit_bytes": 16
    },
    "action_name":"access",
    "arguments":"None"
}
print("xbar access")
test(req)
