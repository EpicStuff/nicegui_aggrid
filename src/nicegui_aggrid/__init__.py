import importlib.metadata

from .agdict import AgDict
from .enterprise import enterprise

__version__: str = importlib.metadata.version('EpicStuff')

__all__ = ['AgDict', 'jailbreak']
