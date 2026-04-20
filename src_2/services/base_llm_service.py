from abc import ABC, abstractmethod


class BaseLLMService(ABC):
    @abstractmethod
    def run(self, target, metrics, selected_metrics, analysis_json=None):
        pass

    @abstractmethod
    def build_system_prompt(self, target):
        pass

    @abstractmethod
    def build_user_prompt(
        self, target, base_context, selected_metrics, analysis_json=None
    ):
        pass
