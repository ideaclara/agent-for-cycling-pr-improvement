import os
import sys
import asyncio

# --- Python 3.14 AnyIO WeakKeyDictionary Patch ---
import anyio._backends._asyncio as anyio_asyncio

_orig_cancel_enter = anyio_asyncio.CancelScope.__enter__


def _patched_cancel_enter(self):
    try:
        return _orig_cancel_enter(self)
    except TypeError as e:
        if "cannot create weak reference to 'NoneType' object" in str(e):
            # Fallback: create a dummy task if called where current_task() is None
            return self
        raise e


anyio_asyncio.CancelScope.__enter__ = _patched_cancel_enter
# -------------------------------------------------

import chainlit as cl
from agent import create_cycling_agent


@cl.on_chat_start
def on_chat_start():
    agent = create_cycling_agent()
    cl.user_session.set("agent", agent)


@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    run_sync = cl.make_async(agent)
    res = await run_sync(message.content)
    await cl.Message(content=str(res)).send()
