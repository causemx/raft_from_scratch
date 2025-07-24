import logging
import asyncio
from configs import CONFIG
from node.raft_node import RaftNode
from node.node_metadata import NodeMetadata
from net.network import NetworkComm


logging.basicConfig(level=logging.INFO, \
                    format='%(asctime)s - %(levelname)s - %(message)s')

nodes = []
def load_config():
    for key in list(CONFIG['nodes'].keys()):
        curr_node = CONFIG['nodes'][key]
        (host, port) = curr_node.split(":")
        port = int(port)
        nodes.append(NodeMetadata(host, port))
    port = CONFIG['common']['listen_port']
    return nodes, port

async def main():
    nodes, port = load_config()
    logging.info(f"nodes: {nodes}")
    network_comm = NetworkComm(nodes, port, 0.25)
    # asyncio.run(network_comm.run())
    node = RaftNode(nodes, port, network_comm)
    # asyncio.run(node.run())
    await asyncio.gather(
        network_comm.run(),
        node.run()
    )

if __name__ == "__main__":
    asyncio.run(main())