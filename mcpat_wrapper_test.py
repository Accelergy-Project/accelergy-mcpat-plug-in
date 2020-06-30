from collections import OrderedDict
from mcpat_wrapper import *

wrapper = McPatWrapper(clean_output_files=False)


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
        "clockrate":999,
        "datawidth":32,
        "type":"fpu"
    },
    "action_name":"instruction",
    "arguments":"None"
}
print("fpu instruction")
test(req)

req["action_name"] = "idle"
print("fpu idle")
test(req)

req["action_name"] = "instruction"
req["attributes"]["type"] = "int_alu"
print("int_alu instruction")
test(req)

req["action_name"] = "idle"
print("int_alu idle")
test(req)

req["action_name"] = "instruction"
req["attributes"]["type"] = "mul_alu"
print("mul_alu instruction")
test(req)

req["action_name"] = "idle"
print("mul_alu idle")
test(req)


# xbar
req = {
    "class_name": "xbar",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
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

# tournament_bp
req = {
    "class_name": "tournament_bp",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
        "local_pred_entries": 2048,
        "local_pred_bits": 2,
        "global_pred_entries": 8192,
        "global_pred_bits": 2,
        "choice_pred_entries": 8192,
        "choice_pred_bits": 2
    },
    "action_name":"access",
    "arguments":"None"
}
print("tournament_bp access")
test(req)

req["action_name"] = "miss"
print("tournament_bp miss")
test(req)

req["action_name"] = "idle"
print("tournament_bp idle")
test(req)


# btb
req = {
    "class_name": "btb",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
        "entries": 4096,
        "block_width": 4,
        "associativity": 2,
        "banks": 2,
    },
    "action_name":"read",
    "arguments":"None"
}
print("btb read")
test(req)

req["action_name"] = "write"
print("btb write")
test(req)


# cpu_regfile
req = {
    "class_name": "cpu_regfile",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
        "type":"int"
    },
    "action_name":"read",
    "arguments":"None"
}
print("cpu_regfile int read")
test(req)

print("cpu_regfile int write")
req["action_name"] = "write"
test(req)

print("cpu_regfile int idle")
req["action_name"] = "idle"
test(req)

print("cpu_regfile fp read")
req["attributes"]["type"] = "fp"
req["action_name"] = "read"
test(req)

print("cpu_regfile fp write")
req["action_name"] = "write"
test(req)

print("cpu_regfile fp idle")
req["action_name"] = "idle"
test(req)


# tlb
req = {
    "class_name": "tlb",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
        "entries":64
    },
    "action_name":"access",
    "arguments":"None"
}
print("tlb access")
test(req)

req["action_name"] = "miss"
print("tlb miss")
test(req)


# renaming_unit
req = {
    "class_name": "renaming_unit",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
    },
    "action_name":"read",
    "arguments":"None"
}
print("renaming_unit read")
test(req)

req["action_name"] = "write"
print("renaming_unit write")
test(req)

req["action_name"] = "idle"
print("renaming_unit idle")
test(req)


# reorder_buffer
req = {
    "class_name": "reorder_buffer",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
        "entries": 192,
    },
    "action_name":"read",
    "arguments":"None"
}
print("reorder_buffer read")
test(req)

req["action_name"] = "write"
print("reorder_buffer write")
test(req)


# load_store_queue
req = {
    "class_name": "load_store_queue",
    "attributes":{
        "technology":"45nm",
        "clockrate":999,
        "datawidth":32,
        "entries": 32,
        "type": "load"
    },
    "action_name":"access",
    "arguments":"None"
}
print("load_store_queue load access")
test(req)

req["attributes"]["type"] = "store"
print("load_store_queue store access")
test(req)
