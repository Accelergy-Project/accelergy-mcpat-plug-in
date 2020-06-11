import re

class McPatComponent:
    """
    Base component to query McPat
    """

    base_properties = {
        "system.number_of_cores": 1
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
        size = interface["attributes"]["size"]                    # size in bytes
        block_size = interface["attributes"]["block_size"]        # block size in bytes
        associativity = interface["attributes"]["associativity"]  # cache associativity
        latency = interface["attributes"]["hit_latency"]          # hit latency in cycles
        mshrs = interface["attributes"]["mshrs"]                  # maximum outstanding requests
        accesses, misses = 0, 0
        if self.interface["action_name"] == "read_access":
            accesses = 1
        if self.interface["action_name"] == "read_miss":
            misses = 1

        self.properties["system.core0.icache.icache_config"] = "%s, %s, %s, 1, %s, %s, 32, 0" % (
            size, block_size, associativity, latency, latency)
        self.properties["system.core0.icache.buffer_sizes"] = "%s, %s, %s, 0" % (
            mshrs, mshrs, mshrs)
        self.properties["system.core0.icache.read_accesses"] = accesses
        self.properties["system.core0.icache.read_misses"] = misses

        if interface["attributes"]["cache_type"] == "icache":
            self.name = "icache"
            self.mcpat_name = "Instruction Cache"
            self.key = ("icache", self.interface["action_name"], self.tech_node, self.clockrate,
                        size, block_size, associativity, latency, mshrs)

    def attr_supported(self):
        return self.interface["attributes"]["cache_type"] == "icache"

    def action_supported(self):
        return self.attr_supported() and self.interface["action_name"] in ["read_access", "read_miss"]
