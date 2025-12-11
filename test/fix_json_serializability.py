from nicegui import app
from epicstuff import Dict
from nicegui_aggrid.fix_json_serializability import load, type_registry

from collections import deque


class my_dict_subclass(dict): ...


type_registry.Dict = Dict
type_registry.deque = deque
storage = load(app.storage.general)

storage.setdefault('test1', deque([deque(), deque([Dict(a=10, b=11), 2, 3]), 4, my_dict_subclass(c=5)]))

# make sure to run twice
assert storage.test1 == deque([deque(), deque([Dict(a=10, b=11), 2, 3]), 4, my_dict_subclass(c=5)])
