import pandas as pd
# ruff: noqa: PLR2004
from epicstuff import rich_try, run_fix_import, run_install_trace
from nicegui import app, ui

import src.__init__, utils.aggrid
from src.utils import load_data


def tmp(grid=None):
	return utils.aggrid.AgDict(
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
	utils.aggrid.jailbreak()

	grid = ui.aggrid({
		'defaultColDef': {'flex': 1, 'sortable': True, 'filter': True, 'resizable': True},
		'groupDisplayType': 'groupRows',
		'groupDefaultExpanded': -1,  # expand all groups
		'animateRows': True,
            }, auto_size_columns=False,
	).classes('h-128')

	agdict.grid = grid
	# print(agdict.grids)
	# ui.button('test2', on_click=agdict.grids[0].update)
	# print(agdict.grids[0].options)

	# grid.options['columnDefs'] = agdict.cols
	# grid.options['rowData'] = agdict.rows.values()
	# grid.update()

	test_counter = 0

	@rich_try
	def test():
		nonlocal test_counter
		test_counter += 1
		print('running test:', test_counter)

		if test_counter == 1:
			agdict.rows.Apple.price = 99
		elif test_counter == 2:
			agdict.rows.Carrot.price += 1
		elif test_counter == 3:
			agdict.rows += {'product': 'pineapple', 'price': 2.5}
		elif test_counter == 4:
			agdict.rows.orange = {'price': 50, 'test': 'testing'}
		elif test_counter == 5:
			del agdict.rows.orange.price
		elif test_counter == 6:
			del agdict.rows.orange

	ui.button('test', on_click=test)
	ui.button('reset', on_click=resetish)
	ui.button('tmp', on_click=tmp2)

	# ui.timer(1, tmp2)


def resetish():
	global agdict
	agdict.rows = [
		{'category': 'Fruit', 'product': 'Apple', 'price': 1.2},
		{'category': 'Fruit', 'product': 'Banana', 'price': 0.9},
		{'category': 'Fruit', 'product': 'Pear', 'price': 1.4},
		{'category': 'Vegetable', 'product': 'Carrot', 'price': 0.7},
		{'category': 'Vegetable', 'product': 'Broccoli', 'price': 1.1},
	]

def tmp2():
	df = pd.DataFrame([
		{'category': 'Fruit', 'product': 'Apple', 'price': 0},
		{'category': 'Fruit', 'product': 'Banana', 'price': 0},
		{'category': 'Fruit', 'product': 'Pear', 'price': 0},
		{'category': 'Vegetable', 'product': 'Carrot', 'price': 0},
		{'category': 'Vegetable', 'product': 'Broccoli', 'price': 0},
	])
	agdict.from_pandas(df)


# agdict = utils.aggrid.AgDict(
# 	columns=(
# 		{'headerName': 'User ID', 'field': 'USERID'},
# 		{'headerName': 'Division', 'field': 'COTDIVISION'},
# 		{'headerName': 'Display Name', 'field': 'DISPLAYNAME'},
# 	),
# 	id_field='USERID',
# )
async def maxtest(env: str = 'dev'):
	data = await load_data('maxtest', env, limit=None)
	agdict.grid = ui.aggrid({'defaultColDef': {'flex': 1}}, theme='balham', auto_size_columns=False)\
		.classes('h-128')
	from time import sleep
	sleep(1)
	agdict.from_pandas(data)


ui.run(main, show=False)

# TODO:
# - test changing id_field
# - test changing the cell that is the id_field
# - test multiple grids
