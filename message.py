import queue
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from node.node_metadata import NodeMetadata


class MessageType(Enum):
    HEARTBEAT = "heartbeat"
    VOTE_REQUEST = "voteRequest"
    VOTE_RESPONSE = "voteResponse"

@dataclass
class Message:
    sender: NodeMetadata
    msg_type: MessageType
    elect_term: int
    data: str = None

class MessageQueue:
    def __init__(self, max_size: int):
        self._send_queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._recv_queue: queue.Queue = queue.Queue(maxsize=max_size)
    
    def send_enqueue(self, message: Message):
        """Add message to send queue"""
        try:
            self._send_queue.put_nowait(message)
        except queue.Empty:
            ("Send queue is full, dropping message")
    
    def send_dequeue(self) -> Optional[Message]:
        """Get message from send queue (non-blocking)"""
        try:
            return self._send_queue.get_nowait()
        except queue.Empty:
            return None
    
    def send_empty(self) -> bool:
        """Check if send queue is empty"""
        return self._send_queue.empty()
    
    def recv_enqueue(self, item):
        self._recv_queue.put(item)
    
    def recv_dequeue(self) -> Message:
        return self._recv_queue.get()

    def recv_empty(self) -> bool:
        return self._recv_queue.empty()

    def recv_qsize(self) -> int:
        return self._recv_queue.qsize()

    def _recv_clear(self):
        with self._recv_queue.mutex:
            self._recv_queue.queue.clear()
    