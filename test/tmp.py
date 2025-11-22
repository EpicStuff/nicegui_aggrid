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
