# nicegui-aggrid

A few (currently only 2) useful objects/functions for working with `nicegui`'s `AgGrid`

## Installation

```bash
pip install nicegui-aggrid
```

## Enterprise

Use AgGrid Enterprise

```python
from nicegui_aggrid import enterprise

enterprise(license_key='YOUR_AG_GRID_ENTERPRISE_LICENSE_KEY')
```

Note: the adding a license key feature is not tested (since I don't have a license key)

## AgDict

Object that can be "connected" to multiple aggrids such that changes to `AgDict.rows` will be updated in all connected aggrids without the use of aggrid.update(), is still work in progress


```python
from nicegui import ui
from nicegui_aggrid import AgDict

agdict = AgDict(
	columns=[
		{'field': 'category', 'rowGroup': True, 'hide': True},
		{'field': 'product'},
		{'field': 'price'},
	],
	rows=[
		{'category': 'Fruit', 'product': 'Apple', 'price': 1.2},
		{'category': 'Fruit', 'product': 'Banana', 'price': 0.9},
		{'category': 'Fruit', 'product': 'Pear', 'price': 1.4},
		{'category': 'Vegetable', 'product': 'Carrot', 'price': 0.7},
		{'category': 'Vegetable', 'product': 'Broccoli', 'price': 1.1},
	],
	id_field='product',
)

agdict.grid = ui.aggrid({'groupDisplayType': 'groupRows'}).classes('h-128')

update_counter = 0
def update():
	global update_counter
	update_counter += 1
	if update_counter == 1:
		agdict.rows.Apple.price = 99
	elif update_counter == 2:
		agdict.rows.Carrot.price += 1
	elif update_counter == 3:
		agdict.rows += {'product': 'pineapple', 'price': 2.5}
	elif update_counter == 4:
		agdict.rows.orange = {'price': 50, 'test': 'testing'}
	elif update_counter == 5:
		del agdict.rows.orange.price
	elif update_counter == 6:
		del agdict.rows.orange


ui.button('update', on_click=update)

ui.run()

```
