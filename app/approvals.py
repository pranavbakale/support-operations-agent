import asyncio
from datetime import UTC, datetime
from typing import Protocol

from redis.asyncio import Redis

from app.schemas import ProposedAction


class ApprovalStore(Protocol):
    async def put(self, action: ProposedAction, ttl_seconds: int) -> None: ...

    async def get(self, action_id: str) -> ProposedAction | None: ...

    async def take(self, action_id: str) -> ProposedAction | None: ...

    async def delete(self, action_id: str) -> bool: ...

    async def ping(self) -> bool: ...


class RedisApprovalStore:
    key_prefix = "support:approval:"

    def __init__(self, client: Redis) -> None:
        self.client = client

    def _key(self, action_id: str) -> str:
        return f"{self.key_prefix}{action_id}"

    async def put(self, action: ProposedAction, ttl_seconds: int) -> None:
        await self.client.set(self._key(action.id), action.model_dump_json(), ex=ttl_seconds)

    async def get(self, action_id: str) -> ProposedAction | None:
        payload = await self.client.get(self._key(action_id))
        return ProposedAction.model_validate_json(payload) if payload else None

    async def take(self, action_id: str) -> ProposedAction | None:
        payload = await self.client.getdel(self._key(action_id))
        return ProposedAction.model_validate_json(payload) if payload else None

    async def delete(self, action_id: str) -> bool:
        return bool(await self.client.delete(self._key(action_id)))

    async def ping(self) -> bool:
        return bool(await self.client.ping())


class InMemoryApprovalStore:
    def __init__(self) -> None:
        self.actions: dict[str, ProposedAction] = {}
        self.lock = asyncio.Lock()

    async def put(self, action: ProposedAction, ttl_seconds: int) -> None:
        del ttl_seconds
        async with self.lock:
            self.actions[action.id] = action

    async def get(self, action_id: str) -> ProposedAction | None:
        action = self.actions.get(action_id)
        if action and action.expires_at > datetime.now(UTC):
            return action
        self.actions.pop(action_id, None)
        return None

    async def take(self, action_id: str) -> ProposedAction | None:
        async with self.lock:
            action = await self.get(action_id)
            if action:
                self.actions.pop(action_id, None)
            return action

    async def delete(self, action_id: str) -> bool:
        async with self.lock:
            return self.actions.pop(action_id, None) is not None

    async def ping(self) -> bool:
        return True
