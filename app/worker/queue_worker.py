from __future__ import annotations
import asyncio
import logging
from typing import Optional

from app.worker.pipeline import PipelineEngine
from contracts.models import IncomingMessage
from contracts.protocols import Queue

logger = logging.getLogger(__name__)


class QueueWorker:
    """Background worker continuously pulling from Queue and processing via PipelineEngine."""

    def __init__(self, queue: Queue, pipeline: PipelineEngine, poll_interval_sec: float = 1.0):
        self.queue = queue
        self.pipeline = pipeline
        self.poll_interval = poll_interval_sec
        self.running = False

    async def run_once(self) -> bool:
        """Processes a single queue item if available. Returns True if an item was processed."""
        item = await self.queue.dequeue()
        if not item:
            return False

        item_id, payload = item
        try:
            msg_data = payload.get("message")
            if msg_data:
                msg = IncomingMessage(**msg_data)
                await self.pipeline.process_message(msg)
            await self.queue.ack(item_id)
            return True
        except Exception as e:
            logger.error("Queue worker job %s failed: %s", item_id, e)
            await self.queue.nack(item_id, str(e), retry_after_sec=30)
            return True

    async def start(self) -> None:
        self.running = True
        while self.running:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self.running = False
