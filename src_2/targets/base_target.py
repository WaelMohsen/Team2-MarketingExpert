from abc import ABC, abstractmethod

class BaseTarget(ABC):
    @abstractmethod
    def select(self, metrics):
        pass
