import logging
import asyncio
import sys
from configs import CONFIG
from node.raft_node import RaftNode
from node.node_metadata import NodeMetadata
from net.network import NetworkComm

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(node_id=None):
    """Load configuration and return all nodes and the port for this specific node"""
    nodes = []
    
    # Load all nodes from config
    for key in list(CONFIG['nodes'].keys()):
        curr_node = CONFIG['nodes'][key]
        (host, port) = curr_node.split(":")
        port = int(port)
        nodes.append(NodeMetadata(host, port))
    
    # Determine which port this instance should use
    if node_id is not None:
        # Use specific node ID (1, 2, or 3)
        if 1 <= node_id <= len(nodes):
            my_port = nodes[node_id - 1].get_port()
        else:
            raise ValueError(f"Invalid node_id {node_id}. Must be between 1 and {len(nodes)}")
    else:
        # Fallback to config default
        my_port = int(CONFIG['common']['listen_port'])
    
    return nodes, my_port

async def main():
    # Parse command line arguments
    node_id = None
    if len(sys.argv) > 1:
        try:
            node_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python main.py [node_id]")
            print("  node_id: 1, 2, or 3 (optional)")
            sys.exit(1)
    
    nodes, port = load_config(node_id)
    logging.info(f"Starting node on port {port}")
    logging.info(f"All nodes in cluster: {[(n.get_host(), n.get_port()) for n in nodes]}")
    
    network_comm = NetworkComm(nodes, port, 0.25)
    node = RaftNode(nodes, port, network_comm)
    
    await asyncio.gather(
        network_comm.run(),
        node.run()
    )

if __name__ == "__main__":
    asyncio.run(main())