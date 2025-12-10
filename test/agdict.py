# ruff: noqa
import pandas as pd
from epicstuff import rich_try, run_install_trace
from nicegui import app, ui

from nicegui_aggrid import enterprise, AgDict


def tmp(grid=None):
	print('test-.5')
	return AgDict(
		options={
			'defaultColDef': {'flex': 1, 'sortable': True, 'filter': True, 'resizable': True, 'editable': True},
			'groupDisplayType': 'groupRows',
			'groupDefaultExpanded': -1,  # expand all groups
			'animateRows': True,
			'rowSelection': {'mode': 'multiRow'},
			'cellSelection': True,
		},
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
		grid=grid,
	)


agdict = tmp()

@rich_try
def main():
	enterprise(None, None, '0000-0000-0000-0000')
	print('test0')

	agdict.grid = ui.aggrid({}, auto_size_columns=False).classes('h-128')
	test_counter = 0

	agdict.rows.agdict.grids[0].options  # make sure this isnt a recursion error

	#TODO: look into test up to 5 then reload then test up to 5 leading to 2 orange rows
	@rich_try
	async def test():
		nonlocal test_counter
		test_counter += 1
		print('running test:', test_counter)

		if test_counter == 1:
			agdict.rows.Apple.price = 99
		elif test_counter == 2:
			agdict.rows.Carrot.price += 9
		elif test_counter == 3:
			agdict.rows += {'product': 'pineapple', 'price': 2.5}
		elif test_counter == 4:
			agdict.rows.orange = {'price': 50, 'test': 'testing'}
		elif test_counter == 5:
			del agdict.rows.orange.price
		elif test_counter == 6:
			del agdict.rows.orange
		elif test_counter == 7:
			df = pd.DataFrame([
				{'category': 'Fruit', 'product': 'Apple', 'price': 0},
				{'category': 'Fruit', 'product': 'Banana', 'price': 0},
				{'category': 'Fruit', 'product': 'Pear', 'price': 0},
				{'category': 'Vegetable', 'product': 'Carrot', 'price': 0},
				{'category': 'Vegetable', 'product': 'Broccoli', 'price': 0},
			])
			agdict.from_pandas(df)
		elif test_counter == 8:
			# todo: this reloads the grid
			agdict.on
			agdict.classes
			agdict.on('test').classes()
		elif test_counter == 9:
			agdict2.rows[0].age = 111
			agdict2.rows[1].name = 'ZZZ'
		elif test_counter == 10:
			agdict.rows.Banana.price = 1234
		elif test_counter == 11:
			agdict.rows.Banana.test = 1234  # todo: i think this should just print a warning instead of erroring
		elif test_counter == 12:
			agdict.rows.test.price = 1234  # todo: this should probably create a new row instead of erroring

	print('test1')
	ui.button('test', on_click=test)
	ui.button('reset', on_click=resetish)
	ui.button('tmp', on_click=agdict.update)

	agdict2 = AgDict(grid=ui.aggrid({
		'columnDefs': [
			{'headerName': 'Name', 'field': 'name'},
			{'headerName': 'Age', 'field': 'age'},
			{'headerName': 'Parent', 'field': 'parent', 'hide': True},
		],
		'rowSelection': {'mode': 'multiRow'},
		'defaultColDef': {},
	}), loading=5)
	pass


def resetish():
	agdict.rows = [
		{'category': 'Fruit', 'product': 'Apple', 'price': 1.2},
		{'category': 'Fruit', 'product': 'Banana', 'price': 0.9},
		{'category': 'Fruit', 'product': 'Pear', 'price': 1.4},
		{'category': 'Vegetable', 'product': 'Carrot', 'price': 0.7},
		{'category': 'Vegetable', 'product': 'Broccoli', 'price': 1.1},
	]


# agdict = utils.aggrid.AgDict(
# 	columns=(
# 		{'headerName': 'User ID', 'field': 'USERID'},
# 		{'headerName': 'Division', 'field': 'COTDIVISION'},
# 		{'headerName': 'Display Name', 'field': 'DISPLAYNAME'},
# 	),
# 	id_field='USERID',
# )
async def maxtest():
	data = pd.DataFrame([
		{'USERID': 'user1', 'COTDIVISION': 'A', 'DISPLAYNAME': 'Alice'},
		{'USERID': 'user2', 'COTDIVISION': 'B', 'DISPLAYNAME': 'Bob'},
		{'USERID': 'user3', 'COTDIVISION': 'A', 'DISPLAYNAME': 'Charlie'},
	])
	agdict.from_pandas(data)

print('test-1')
ui.run(main, show=False, reload=False)

# TODO:
# - test changing id_field
# - test changing the cell that is the id_field
# - test multiple grids
