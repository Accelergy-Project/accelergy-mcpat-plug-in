from mcpat_wrapper import *

wrapper = McPatWrapper(clean_output_files=False, verbose=False)


def test(interface):
    print("action supported ", wrapper.primitive_action_supported(interface))
    print("action energy    ", wrapper.estimate_energy(interface), "pJ")
    print("area supported   ", wrapper.primitive_area_supported(interface))
    print("area             ", wrapper.estimate_area(interface), "mm^2\n")


glob_attrs = {
    "technology": "45nm",
    "datawidth": 32,
    "clockrate": 999,
    "device_type": "lop"
}

# cache icache
req = {
   "class_name":"cache",
   "attributes":{
      **glob_attrs,
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
      "write_buffer_size":8
   },
   "action_name":"read_hit",
   "arguments":"None"
}
print("cache icache read_hit")
test(req)

req["action_name"] = "read_miss"
print("cache icache read_miss")
test(req)


# cache dcache
req = {
   "class_name":"cache",
   "attributes":{
      **glob_attrs,
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
      "write_buffer_size":8
   },
   "action_name":"read_hit",
   "arguments":"None"
}
print("cache dcache read_hit")
test(req)

req["action_name"] = "read_miss"
print("cache dcache read_miss")
test(req)

req["action_name"] = "write_hit"
print("cache dcache write_hit")
test(req)

req["action_name"] = "write_miss"
print("cache dcache write_miss")
test(req)


# cache l2cache
req = {
    "class_name":"cache",
   "attributes":{
       **glob_attrs,
      "n_rd_ports":1,
      "n_wr_ports":1,
      "n_rdwr_ports":1,
      "n_banks":4,
      "cache_type":"l2cache",
      "size":2097152,
      "associativity":8,
      "data_latency":20,
      "block_size":64,
      "mshr_size":20,
      "tag_size":64,
      "write_buffer_size":8
   },
   "action_name":"read_hit",
   "arguments":"None"
}
print("cache l2cache read_hit")
test(req)

req["action_name"] = "read_miss"
print("cache l2cache read_miss")
test(req)

req["action_name"] = "write_hit"
print("cache l2cache write_hit")
test(req)

req["action_name"] = "write_miss"
print("cache l2cache write_miss")
test(req)


# func units
req = {
    "class_name": "func_unit",
    "attributes":{
        **glob_attrs,
        "type":"fpu"
    },
    "action_name":"access",
    "arguments":"None"
}
print("fpu access")
test(req)

req["action_name"] = "idle"
print("fpu idle")
test(req)

req["action_name"] = "access"
req["attributes"]["type"] = "int_alu"
print("int_alu access")
test(req)

req["action_name"] = "idle"
print("int_alu idle")
test(req)

req["action_name"] = "access"
req["attributes"]["type"] = "mul_alu"
print("mul_alu access")
test(req)

req["action_name"] = "idle"
print("mul_alu idle")
test(req)


# xbar
req = {
    "class_name": "xbar",
    "attributes":{
        **glob_attrs,
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
        **glob_attrs,
        "local_pred_entries": 2048,
        "local_pred_bits": 2,
        "global_pred_entries": 8192,
        "global_pred_bits": 2,
        "choice_pred_entries": 8192,
        "choice_pred_bits": 2
    },
    "action_name":"hit",
    "arguments":"None"
}
print("tournament_bp hit")
test(req)

req["action_name"] = "miss"
print("tournament_bp miss")
test(req)


# btb
req = {
    "class_name": "btb",
    "attributes":{
        **glob_attrs,
        "entries": 4096,
        "block_width": 4,
        "associativity": 2,
        "banks": 2
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
        **glob_attrs,
        "type":"int",
        "phys_size": 256,
        "issue_width": 8
    },
    "action_name":"read",
    "arguments":"None"
}
print("cpu_regfile int read")
test(req)

print("cpu_regfile int write")
req["action_name"] = "write"
test(req)

print("cpu_regfile fp read")
req["attributes"]["type"] = "fp"
req["action_name"] = "read"
test(req)

print("cpu_regfile fp write")
req["action_name"] = "write"
test(req)


# tlb
req = {
    "class_name": "tlb",
    "attributes":{
        **glob_attrs,
        "entries":64
    },
    "action_name":"hit",
    "arguments":"None"
}
print("tlb hit")
test(req)

req["action_name"] = "miss"
print("tlb miss")
test(req)


# renaming_unit
req = {
    "class_name": "renaming_unit",
    "attributes":{
        **glob_attrs,
        "decode_width": 8,
        "commit_width": 8,
        "phys_irf_size": 256,
        "phys_frf_size": 256
    },
    "action_name":"read",
    "arguments":"None"
}
print("renaming_unit read")
test(req)

req["action_name"] = "write"
print("renaming_unit write")
test(req)


# reorder_buffer
req = {
    "class_name": "reorder_buffer",
    "attributes":{
        **glob_attrs,
        "entries": 192
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
        **glob_attrs,
        "entries": 32,
        "type": "load",
        "ports": 2
    },
    "action_name":"load",
    "arguments":"None"
}
print("load_store_queue load load")
test(req)

req["action_name"] = "store"
print("load_store_queue load store")
test(req)

req["attributes"]["type"] = "store"
req["action_name"] = "load"
print("load_store_queue store load")
test(req)

req["action_name"] = "store"
print("load_store_queue store store")
test(req)


# fetch_buffer
req = {
    "class_name": "fetch_buffer",
    "attributes":{
        **glob_attrs,
        "entries": 64
    },
    "action_name":"access",
    "arguments":"None"
}
print("fetch_buffer access")
test(req)


# decoder
req = {
    "class_name": "decoder",
    "attributes":{
        **glob_attrs,
        "width": 8
    },
    "action_name":"access",
    "arguments":"None"
}
print("decoder access")
test(req)


# inst_queue
req = {
    "class_name": "inst_queue",
    "attributes":{
        **glob_attrs,
        "type": "int",
        "entries": 32,
        "issue_width": 8
    },
    "action_name":"read",
    "arguments":"None"
}
print("inst_queue int read")
test(req)

req["action_name"] = "write"
print("inst_queue int write")
test(req)

req["action_name"] = "wakeup"
print("inst_queue int wakeup")
test(req)

req["attributes"]["type"] = "fp"
req["action_name"] = "read"
print("inst_queue fp read")
test(req)

req["action_name"] = "write"
print("inst_queue fp write")
test(req)

req["action_name"] = "wakeup"
print("inst_queue fp wakeup")
test(req)
