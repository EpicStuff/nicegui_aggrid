from nicegui import app
from epicstuff import Dict
from nicegui_aggrid.fix_json_serializability import load, type_registry

from collections import deque

type_registry.Dict = Dict
type_registry.deque = deque
storage = load(app.storage.general)

storage.setdefault('test1', deque([deque([deque([1, 2, 3]), 4, 5]), 6]))

print(storage)
