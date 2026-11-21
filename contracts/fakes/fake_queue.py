from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, Tuple
from contracts.protocols import Queue


class FakeQueue:
    def __init__(self):
        self._items: Dict[str, Dict[str, Any]] = {}
        self._pending: list[str] = []
        self._counter: int = 0
        self._lock = asyncio.Lock()

    async def enqueue(self, payload: Dict[str, Any], priority: int = 0) -> str:
        async with self._lock:
            self._counter += 1
            item_id = f"q_{self._counter}"
            self._items[item_id] = {
                "payload": payload,
                "priority": priority,
                "status": "pending",
                "retries": 0,
            }
            # High priority first
            if priority > 0:
                self._pending.insert(0, item_id)
            else:
                self._pending.append(item_id)
            return item_id

    async def dequeue(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        async with self._lock:
            if not self._pending:
                return None
            item_id = self._pending.pop(0)
            self._items[item_id]["status"] = "processing"
            return item_id, self._items[item_id]["payload"]

    async def ack(self, item_id: str) -> None:
        async with self._lock:
            if item_id in self._items:
                self._items[item_id]["status"] = "done"

    async def nack(self, item_id: str, error: str, retry_after_sec: int = 60) -> None:
        async with self._lock:
            if item_id in self._items:
                self._items[item_id]["status"] = "failed"
                self._items[item_id]["error"] = error
                self._items[item_id]["retries"] += 1
                if self._items[item_id]["retries"] <= 3:
                    self._pending.append(item_id)
