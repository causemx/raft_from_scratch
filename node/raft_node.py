import asyncio
import time
import random
import logging
from enum import Enum
from typing import Optional
from node.node_metadata import NodeMetadata
from net import network_util
from net.network import NetworkComm
from message import Message, MessageType


logging.basicConfig(level=logging.INFO, \
                    format='%(asctime)s - %(levelname)s - %(message)s')

class NodeState(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

class RaftNode():
    def __init__(self, nodes_list: list, port: int, network_comm: NetworkComm):
        self.logger = logging.getLogger()
        self._state: NodeState = NodeState.FOLLOWER
        self._election_timeout: Optional[int] = None
        self._current_term: int = 0
        self._current_leader: Optional[NodeMetadata] = None
        self._nodes: list = nodes_list
        self._neighbors: list = []
        self._cluster_size: int = len(nodes_list)
        self._votes_needed: int = self._cluster_size // 2 + 1
        self._host: str = 'localhost'
        self._port: int = port
        self._server: Optional[asyncio.Server] = None
        self._ip_address: str = network_util.get_localhost_ip_addr()
        self._network_comm: NetworkComm = network_comm

    def _populate_neighbor(self):
        for host, port in self._nodes:
            if port != self._port:
                neighbor = NodeMetadata(host=host, port=port)
                self._neighbors.append(neighbor)

    async def run(self):
        """run this node's raft algorithm forever"""
        self._populate_neighbors()
        logging.info("Neighbors: {}".format(self._neighbors))
        while True:
            await self._process_node()

    def _populate_neighbors(self):
        for node in self._nodes:
            if not self._network_comm.is_node_me(node):
                self._neighbors.append(node)
        
        
    async def _process_node(self):
        match self._state:
            case NodeState.LEADER:
                await self._process_leader()
            case NodeState.CANDIDATE:
                await self._process_candidate()
            case NodeState.FOLLOWER:
                await self._process_follower()

    async def _process_leader(self):
        self._current_term += 1
        self.logger.debug("Node entering LEADER STATE with term {}".format(self._current_term))
        sender = self._get_node_metadata()
        message = Message(sender, MessageType.HEARTBEAT, self._current_term)
        
        for neighbor in self._neighbors:
            await self._network_comm.send_data(message, neighbor)
        
        leader_timeout = self._generate_timeout()
        self.logger.debug(f"Candidate timeout: {leader_timeout}")
        start = time.time()
        heartbeat_response = []
        
        while not self._timeout(start, leader_timeout):
            while self._network_comm.message_queue.recv_empty() and not self._timeout(start, leader_timeout):
                pass
            if self._timeout(start, leader_timeout):
                self._state = NodeState.FOLLOWER
                break
            
            msg = self._network_comm.message_queue.recv_dequeue()
            if not self._validate_message_sender(msg):
                continue
            if msg.msg_type == MessageType.HEARTBEAT and msg.sender not in heartbeat_response:
                heartbeat_response.append(msg.sender)
            
            if msg.msg_type == MessageType.HEARTBEAT and msg.elect_term > self._current_term:
                self.logger.info("Received a heartbeat from a leader with a higher term")
            
            # What is this step for?
            if len(heartbeat_response) + 1 >= self._votes_needed:
                return
        
        if self._state == NodeState.FOLLOWER:
            self.logger.info("Failed to get majority ack in allocated time, step down") 
            self._current_leader = None  
        

    async def _process_candidate(self):
        self._current_term += 1
        self.logger.debug("Node entering CANDIDATE STATE with term {}".format(self._current_term))
        sender = self._get_node_metadata()
        message = Message(sender, MessageType.VOTE_REQUEST, self._current_term)

        for neighbor in self._neighbors:
            await self._network_comm.send_data(message, neighbor)

        candidate_timeout = self._generate_timeout()
        self.logger.debug("Candidate timeout: {}".format(candidate_timeout))
        start = time.time()
        voted_for_me = []
        
        while not self._timeout(start, candidate_timeout):
            while self._network_comm.message_queue.recv_empty() and not self._timeout(start, candidate_timeout):
                pass
            if self._timeout(start, candidate_timeout):
                break
            msg = self._network_comm.message_queue.recv_dequeue()
            if not self._validate_message_sender(msg):
                continue
            if msg.get_type() == MessageType.VOTE_RESPONSE and msg.get_sender not in voted_for_me:
                self.logger.info("Got vote from {}".format(msg.get_sender()))
                voted_for_me.append(msg.get_sender())
            if len(voted_for_me) + 1 >= self._votes_needed:
                self.logger.info("Got enough votes to enter leader state")
                self._state = NodeState.LEADER
                return

        if self._state == NodeState.CANDIDATE:
            self.logger.info("Failed to get votes, falling back to follower state")
        self._state = NodeState.FOLLOWER
        self._current_term -= 1
        

    async def _process_follower(self):
        self._election_timeout = self._generate_timeout()
        print(f"Election timeout was generated: {self._election_timeout}ms")
        voted_this_term = False
        start = time.time()
        while not self._timeout(start, self._election_timeout):
            if not self._network_comm.message_queue.recv_empty():
                msg: Message = self._network_comm.message_queue.recv_dequeue()
                logging.info(f"Received a message: {msg.sender}, {msg.msg_type}, term: {msg.elect_term}")
            
                # Joining the cluster when a leader has already been established
                if self._current_leader is None and msg.msg_type == MessageType.HEARTBEAT:
                    self.logger.info(f"Received a heartbeat from the new leader {msg.sender_id}")
                    self._current_leader = msg.sender_id
                    self._current_term = msg.elect_term
                    self._send_heartbeat_response()
                    return

                # Heartbeat from current leader
                if msg.get_sender() == self._current_leader and msg.get_type() == MessageType.HEARTBEAT:
                    self.logger.info("Received heartbeat from leader, remaining in follower state")
                    self._send_heartbeat_response()
                    return

                # Have a leader, but a new leader with a higher term has been elected
                if msg.get_sender() != self._current_leader and msg.get_type() == MessageType.HEARTBEAT \
                        and msg.get_election_term() > self._current_term:
                    self.logger.info(f"Received a heartbeat from the new leader {msg.sender_id}")
                    self._current_leader = msg.sender_id
                    self._current_term = msg.elect_term
                    self._send_heartbeat_response()
                    return

                # Vote request
                if msg.get_sender() != self._current_leader and msg.get_type() == MessageType.VOTE_REQUEST \
                        and msg.get_election_term() > self._current_term and not voted_this_term:
                    self.logger.info(f"Received vote request from {msg.sender_id}, sending vote response")
                    sender = self._get_node_metadata()
                    message = Message(sender, MessageType.VOTE_RESPONSE, self._current_term)
                    self.logger.info(f"Sending vote response: {message}")
                    await self._network_comm.send_data(message, msg.get_sender())
                    voted_this_term = True

        self.logger.info("Election timeout reached, entering candidate state")
        self._state = NodeState.CANDIDATE
    
    def _validate_message_sender(self, msg: Message) -> bool:
        if msg.sender not in self._neighbors:
            logging.info("Recv message not in neighnors")
            return False
        else:
            return True
    
    def _get_node_metadata(self) -> NodeMetadata:
        return NodeMetadata(self._ip_address, self._port)
    
    def _timeout(self, start: float, timeout: int) -> bool:
        return (time.time() - start) * 1000  > timeout

    def _generate_timeout(self) -> int:
        """ Random timeout between 150-300 ms """
        return random.randint(150, 300)
    
    async def _send_heartbeat_response(self):
        message: Message = Message(self._get_node_metadata(), MessageType.HEARTBEAT, self._current_term)
        await self._network_comm.send_data(message, self._current_leader)