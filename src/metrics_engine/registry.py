KPI_REGISTRY = {}


def register_target(target_name):

    def decorator(func):
        KPI_REGISTRY[target_name] = func
        return func

    return decorator
