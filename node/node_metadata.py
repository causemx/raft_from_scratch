from net import network_util

class NodeMetadata:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
    
    def __eq__(self, value):
        if not isinstance(value, NodeMetadata):
            return False
        return network_util.are_ipaddrs_equal(self._host, value.get_host())\
            and self._port == value.get_port()
    
    def get_host(self) -> str:
        return self._host
    
    def get_port(self) -> int:
        return self._port