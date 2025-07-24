import asyncio
import pytest
import time
from typing import List
import json
from node.node_metadata import NodeMetadata
from message import Message, MessageType, MessageQueue
from net import network, network_util


class TestMessageQueue:
   def test_queue_basic(self):
        queue = MessageQueue(max_size=10)
        test_message = Message(
            sender=NodeMetadata("localhost", 8088),
            msg_type=MessageType.HEARTBEAT,
            elect_term=1,
            data="test",
        )
        queue.send_enqueue(test_message)
        assert not queue.send_empty()
        
        queue.send_dequeue()
        assert queue.send_empty()

class TestNetworkUtil:
    def test_is_ip_localhost(self):
        ip = "8.8.8.8"
        ip_2 = "localhost"
        assert not network_util.is_ippaddr_localhost(ip)
        assert network_util.is_ippaddr_localhost(ip_2)
        

class TestNetworkComm:
    pass

class TestNetworkCommIntegration:
    pass
