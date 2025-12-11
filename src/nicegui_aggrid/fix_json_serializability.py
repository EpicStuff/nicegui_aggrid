# ruff: noqa: SLF001
from typing import Any
from epicstuff import Dict
from collections.abc import Mapping, Iterable, Callable
from nicegui.json import orjson_wrapper as json
import orjson
from nicegui.observables import ObservableDict, ObservableList


# make nicegui run to_json on subclasses
json.ORJSON_OPTS |= orjson.OPT_PASSTHROUGH_SUBCLASS

# to json
original_converter = json._orjson_converter
def to_json(obj: Any) -> Any:
	# treat nicegui dict and list as normal dict and list
	if isinstance(obj, ObservableDict):
		return dict(obj)
	if isinstance(obj, ObservableList):
		return dict(obj)

	if hasattr(obj, '_to_json'):
		data = obj._to_json()
	elif isinstance(obj, Mapping):
		data = dict(obj)
	elif isinstance(obj, Iterable):
		data = list(obj)
	else:
		return original_converter(obj)
	return {'__type__': obj.__class__.__name__, '__data__': data}


json._orjson_converter = to_json

# from json
def load(storage: dict) -> Dict:
	for key, value in storage.items():
		storage[key] = _convert(value)
	return Dict(storage, _convert=False)


def _convert(item: Any) -> Any:
	# if its a list, convert each item in the list
	if isinstance(item, list):
		return [_convert(v) for v in item]
	# if its a dict
	if isinstance(item, dict):
		# if it has __type__ and __data__, convert the __data__ to its original type
		if '__type__' in item and isinstance(type_name := item['__type__'], str) and '__data__' in item:
			# recursivly convert the __data__'s items
			data = _convert(item['__data__'])
			# get the type object from the type registry
			decoder = type_registry.get(type_name)
			# if found, use it to decode the data
			if decoder is not None:
				# if decoder has from_json, use it
				if hasattr(decoder, 'from_json') and callable(decoder.from_json):
					return decoder.from_json(data)
				return decoder(data)
			return data
		# else, convert each value in the dict
		return {key: _convert(value) for key, value in item.items()}
	# else, return the item as is
	return item


type_registry: Dict[str, Callable] = Dict()

def register_type(**kwargs) -> None:
	'''Register types for JSON serialization/deserialization.'''
	for key, value in kwargs.items():
		type_registry[key] = value
