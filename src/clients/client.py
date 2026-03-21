from abc import ABC, abstractmethod
import functools
import asyncio
from loguru import logger
from typing import Self

class Client(ABC):

    def __init__(self) -> None:
        self._connected = False
        self._logger = logger.bind(client=self.__class__.__name__)

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> None:
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()