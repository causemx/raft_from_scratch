import ipaddress
import socket

def get_localhost_ip_addr() -> str:
    host = socket.gethostname()
    local_ip = socket.gethostbyname(host)
    return local_ip

def are_ipaddrs_equal(addr1: str, addr2: str) -> bool:
    """Compare two IP addresses for equality, handling different formats"""
    if addr1 == addr2:
        return True
    if addr1 == "localhost":
        r_addr1 = "127.0.0.1"
    else:
        r_addr1 = addr1
    if addr2 == "localhost":
        r_addr2 = "127.0.0.1"
    else:
        r_addr2 = addr2
    return r_addr1 == r_addr2

def is_ippaddr_localhost(ip_addr: str) -> bool:
    """Check if IP address represents localhost"""
    localhost_addrs = {"127.0.0.1", "::1", "localhost"}
    
    # Handle localhost string
    if ip_addr.lower() == "localhost":
        return True
        
    try:
        ip = ipaddress.ip_address(ip_addr)
        return ip.is_loopback
    except ValueError:
        return ip_addr in localhost_addrs