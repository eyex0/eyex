from abc import ABC, abstractmethod

class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def generate(self, *args, **kwargs):
        ...

    @abstractmethod
    async def stream(self, *args, **kwargs):
        ...

    @abstractmethod
    async def embed(self, *args, **kwargs):
        ...

    @abstractmethod
    async def rerank(self, *args, **kwargs):
        ...

    @abstractmethod
    async def evaluate(self, *args, **kwargs):
        ...

    @abstractmethod
    async def classify(self, *args, **kwargs):
        ...

    @abstractmethod
    async def summarize(self, *args, **kwargs):
        ...

    @abstractmethod
    async def extract(self, *args, **kwargs):
        ...

    @abstractmethod
    async def translate(self, *args, **kwargs):
        ...

    @abstractmethod
    async def moderate(self, *args, **kwargs):
        ...
