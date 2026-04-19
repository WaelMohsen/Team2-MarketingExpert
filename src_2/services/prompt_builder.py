import os

TARGET_PROMPT_FILES = {
    "revenue": "revenue_growth.md",
    "acquisition": "customer_acquisition.md",
    "retention": "customer_retention.md",
    "satisfaction": "customer_satisfaction.md",
}


class PromptBuilder:
    def __init__(self, prompts_dir="prompts"):
        self.prompts_dir = prompts_dir

    def load(self, filename):
        path = os.path.join(self.prompts_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading prompt {filename}: {e}")
            return ""

    def load_target_prompt(self, target):
        filename = TARGET_PROMPT_FILES.get(target)
        if not filename:
            return ""
        return self.load(filename)
