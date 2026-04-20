from abc import ABC, abstractmethod


class BaseTarget(ABC):
    @abstractmethod
    def select_target(self, metrics):
        pass
