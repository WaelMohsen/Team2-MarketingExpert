import json

from src.evaluation.services.aggregate_logs import aggregate_logs


def main() -> None:
    result = aggregate_logs()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
