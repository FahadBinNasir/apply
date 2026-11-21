from __future__ import annotations
from typing import Any, Dict, List, Optional
from contracts.models import IncomingMessage
from contracts.protocols import IntakeSource


class FakeIntakeSource:
    def __init__(self, initial_messages: Optional[List[IncomingMessage]] = None):
        self.messages: List[IncomingMessage] = initial_messages or []
        self.connected: bool = True
        self.qr_code: Optional[str] = None

    def add_message(self, message: IncomingMessage) -> None:
        self.messages.append(message)

    async def poll_or_receive(self) -> List[IncomingMessage]:
        res = list(self.messages)
        self.messages.clear()
        return res

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "engine": "fake_waha",
            "battery": 100,
            "phone": "+923001234567",
        }

    def get_qr(self) -> Optional[str]:
        return self.qr_code
