import functools
import logging

logger = logging.getLogger(__name__)
# Définition d'un décorateur pour afficher le nom de la fonction
def trace_function_log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Si la fonction est appelée depuis une instance, elle aura `self` en premier argument
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
            logger.info(f"Fonction: {class_name}.{func.__name__} ")
        else:
            logger.info(f"Fonction: {class_name}.{func.__name__}")
        return func(*args, **kwargs)
    return wrapper
