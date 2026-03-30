import typing

KPI_REGISTRY: dict[str, typing.Callable] = {}

def register_target(target_name):
    """Decorator to register a KPI calculation function for a specific target KPI."""
    
    def decorator(func):
        '''Decorator to register a KPI calculation function for a specific target KPI.
        This decorator adds the provided function to the KPI_REGISTRY under the specified target name.'''
        KPI_REGISTRY[target_name] = func
        return func

    return decorator