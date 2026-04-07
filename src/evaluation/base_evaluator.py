class BaseEvaluator:

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, data: dict) -> dict:
        raise NotImplementedError