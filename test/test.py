# from nicegui_aggrid import AgDict

# aggrid = AgDict(
# 	options={
# 		'defaultColDef': {'flex': 1, 'sortable': True, 'filter': True, 'resizable': True},
# 		'groupDisplayType': 'groupRows',
# 		'groupDefaultExpanded': -1,  # expand all groups
# 		'animateRows': True,
# 	},
# 	columns=[
# 		{'field': 'category', 'rowGroup': True, 'hide': True},
# 		{'field': 'product'},
# 		{'field': 'price'},
# 	],
# 	rows=[
# 		{'category': 'Fruit', 'product': 'Apple', 'price': 1.2},
# 		{'category': 'Fruit', 'product': 'Banana', 'price': 0.9},
# 		{'category': 'Fruit', 'product': 'Pear', 'price': 1.4},
# 		{'category': 'Vegetable', 'product': 'Carrot', 'price': 0.7},
# 		{'category': 'Vegetable', 'product': 'Broccoli', 'price': 1.1},
# 	],
# 	id_field='product',
# )

from epicstuff import Dict
from collections import UserDict

a = Dict(a=1, _convert=True)
# a = {'a': 1}
# a = UserDict(a=1)
b = Dict(b=2, _convert=True, _create=True)

c = a | b

print(c)
