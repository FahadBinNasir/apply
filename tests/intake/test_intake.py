import asyncio
import json
import time
import pytest

from app.intake.handler import WebhookIntakeHandler
from app.intake.security import sign_payload, sign_waha_payload, verify_webhook_signature
from app.intake.waha import parse_waha_message
from contracts.fakes import FakeInboxRepo, FakeQueue


def test_hmac_and_anti_replay():
    secret = "test_super_secret_key"
    ts = int(time.time())
    payload = b'{"event": "message", "body": "test"}'

    sig = sign_payload(payload, secret, ts)
    is_valid, err = verify_webhook_signature(payload, secret, sig, str(ts))
    assert is_valid
    assert err is None

    # Invalid signature
    is_valid, err = verify_webhook_signature(payload, secret, "wrong_sig", str(ts))
    assert not is_valid
    assert "Invalid webhook HMAC signature" in err

    # Expired timestamp (350s drift)
    old_ts = ts - 350
    old_sig = sign_payload(payload, secret, old_ts)
    is_valid, err = verify_webhook_signature(payload, secret, old_sig, str(old_ts))
    assert not is_valid
    assert "Timestamp drift exceeded" in err

    # WAHA native HMAC test (raw body digest)
    waha_sig = sign_waha_payload(payload, secret)
    is_valid_waha, err_waha = verify_webhook_signature(payload, secret, waha_hmac_header=waha_sig)
    assert is_valid_waha
    assert err_waha is None

    # WAHA sha256= prefix support
    is_valid_prefix, _ = verify_webhook_signature(payload, secret, waha_hmac_header=f"sha256={waha_sig}")
    assert is_valid_prefix

    # Bad WAHA HMAC
    is_valid_bad, err_bad = verify_webhook_signature(payload, secret, waha_hmac_header="sha256=deadbeef")
    assert not is_valid_bad
    assert "Invalid WAHA HMAC" in err_bad


def test_waha_parser():
    # 1. Group message
    group_payload = {
        "event": "message",
        "payload": {
            "id": "true_1203630248572918@g.us_3EB012345",
            "from": "1203630248572918@g.us",
            "body": "DevOps Engineer hiring post at Paysys Labs",
            "hasMedia": False,
            "_data": {"notifyName": "Alumni Member"},
        },
    }
    msg_group = parse_waha_message(group_payload)
    assert msg_group.is_group
    assert not msg_group.is_channel
    assert "1203630248572918" in msg_group.chat_id
    assert msg_group.sender == "Alumni Member"
    assert msg_group.message_hash

    # 2. Channel message
    channel_payload = {
        "event": "message",
        "payload": {
            "id": "channel_msg_01",
            "from": "1203631982736451@newsletter",
            "body": "Storage & Compute Intern Opportunity",
            "hasMedia": False,
        },
    }
    msg_channel = parse_waha_message(channel_payload)
    assert msg_channel.is_channel
    assert not msg_channel.is_group


def test_intake_handler_capture_first_and_idempotent():
    async def _test():
        inbox_repo = FakeInboxRepo()
        queue = FakeQueue()
        secret = "my_secret"
        handler = WebhookIntakeHandler(inbox_repo, queue, webhook_secret=secret)

        ts = int(time.time())
        payload = {
            "payload": {
                "id": "msg_unique_101",
                "from": "1203630248572918@g.us",
                "body": "We're Hiring – DevOps Engineer at Paysys Labs",
            }
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = sign_payload(raw_body, secret, ts)

        # 1. First capture succeeds
        ok, msg, item_id = await handler.process_incoming(payload, raw_body, sig, str(ts))
        assert ok
        assert item_id is not None
        assert len(inbox_repo.inbox_items) == 1

        # Check queue has item
        deq = await queue.dequeue()
        assert deq is not None
        assert deq[1]["inbox_id"] == item_id

        # 2. Duplicate transmission is ignored without error
        ok2, msg2, item_id2 = await handler.process_incoming(payload, raw_body, sig, str(ts))
        assert ok2
        assert "Duplicate" in msg2
        assert item_id2 is None
        # Queue should not receive another item
        assert await queue.dequeue() is None

    asyncio.run(_test())
