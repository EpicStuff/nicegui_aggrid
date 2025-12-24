import asyncio
from abc import ABC
from collections.abc import Callable, Iterator, Sequence
from typing import Any, Self, overload

from epicstuff import Dict, wrap, console
from nicegui import ui, events


class AgDict:
	'''A Dict that can be "connected" to multiple aggrids such that changes to this Dict will be updated in all connected aggrids without the use of aggrid.update().'''

	loading_sentinel = '__loading'

	def __init__(
		self,
		options: dict | None = None, columns: list | tuple | None = None, rows: list | tuple | None = None,  # pyright: ignore[reportRedeclaration]
		id_field: str | None = None, grid: ui.aggrid | None = None, create_grid: bool = False, loading: int = 1,
		**kwargs: Any,
	) -> None:
		'''Initialize an AgDict instance.

		:param options: Aggrid options, ~~will get passed to the aggrid on creation if aggrid's options are empty.~~ Overwrites aggrid's options.
		:param columns: List or tuple of column definitions. What would normally be in options["columnDefs"]. Overwrites options.
		:param rows: List or tuple of row data. What would normally be in options["rowData"]. Overwrites options.
		:param id_field: The field to use as the unique identifier for rows.
		:param grid: An optional NiceGUI aggrid instance to connect to this AgDict. Can be added latter with the `grid` attribute.
		:param create_grid: If True, create a new NiceGUI aggrid instance during initialization.
		:param loading: Number of loading skeleton rows to show when no rows are provided.
		'''
		options: Dict = Dict(options, _convert=True, _create=True)
		if grid:
			# merge grid.options with option, options taking precedence
			options = options.__ror__(grid.options)
		# if cols not already set, get them from the grid
		if not columns and options.get('columnDefs'):
			columns = options.columnDefs
		# if rows not already set, get them from the grid
		if not rows and options.get('rowData'):
			rows = options.rowData
		# make aggrid use the id_field
		if ':getRowId' in options: ...  # TODO: maybe extract id_field from existing getRowId
		# enable loading skeletons if needed
		if loading:
			# ToDo: make loading optionaly cell or row based
			options.defaultColDef[':cellRendererSelector'] = f"p => p.data?.[p.colDef.field] === '{self.loading_sentinel}' ? {{component: 'agSkeletonCellRenderer'}} : null"
			options.defaultColDef[':valueGetter'] = f"p => p.data?.[p.colDef.field] === '{self.loading_sentinel}' ? null : p.data?.[p.colDef.field]"
			# if not rows:
			# 	print('Info: cellDataType being set to False since loading')
			# 	options.defaultColDef.cellDataType = False

		super().__init__()

		self.grids = []
		self.edit_queue = Dict()
		self._loading = loading
		self.id_field = id_field
		self.cols = columns  # gets auto converted to _AgCols
		self.rows = rows  # gets auto converted to _AgRows  # pyright: ignore[reportAttributeAccessIssue]
		self.options = options or {}  # note: does not sync with rows/cols, just gets overwritten
		self.grid = grid or (ui.aggrid(self.options, **kwargs) if create_grid else None)

	# properties
	@property
	def options(self) -> Dict:
		return self._options
	@options.setter
	def options(self, val: dict) -> None:
		# convert to Dict if not already
		if not isinstance(val, Dict):
			val = Dict(val, _convert=True, _create=True)
		# overwrite rowData if rows are set
		if self.rows:
			val.rowData = self.rows.values()
		# maybe also do the same with cols
		# update self
		self._options = val
		for grid in self.iter_grids():
			grid.run_grid_method('updateGridOptions', val)		# if changing id_field and rows is allready set
	@property
	def id_field(self) -> str | None:
		return self._id_field
	@id_field.setter
	def id_field(self, val: str | None) -> None:
		self._id_field = val
		if val is None:
			return
		# if rows is set, update its id_field
		if hasattr(self, 'rows'):
			# set the new id_field
			self.rows.id_field = val
			# recreate all rows with the new id_field
			self.rows = self.rows.values()
		# if there are grids, update their getRowId option
		for grid in self.iter_grids():
			grid.run_grid_method('setGridOption', ':getRowId', f'params => params.data.{val}')
	@property
	def cols(self) -> '_AgCols':
		return self._cols
	@cols.setter
	def cols(self, val: '_AgCols | list | tuple | None') -> None:
		assert not isinstance(val, _AgCols), 'look into this'
		val = _AgCols(val, self)
		for grid in self.iter_grids():
			grid.run_grid_method('setGridOption', 'columnDefs', val.values())
		self._cols = val
	@property
	def rows(self) -> '_AgRows':
		return self._rows
	@rows.setter
	def rows(self, val: '_AgRows | list | tuple | None') -> None:
		# if new rows or if called by __setitem__ with key id_field
		if not isinstance(val, _AgRows):
			# if no rows and loading enabled, create loading rows
			if val is None and self._loading:
				if self.cols is None:
					raise ValueError('Columns must be set to use loading.')
				val = [dict.fromkeys(self.cols, '__loading') for _ in range(self._loading)]
			# if id_field is still not set, set it to __index
			if self.id_field is None:
				console.print('[bright_black]Debug: id_field being set to __index since rows are being set.[/]')
				self.id_field = '__index'
			# create new _AgRows and update all connected grids
			val = _AgRows(val, self, self.id_field)  # pyright: ignore[reportArgumentType]
			for grid in self.iter_grids():
				grid.run_grid_method('setGridOption', 'rowData', val.values())
		# else, called by __iadd__ from _AgRows, grid allready updated, do nothing extra
		# finally, set self._rows
		self._rows = val
	@property
	def grid(self) -> Any:
		if len(self.grids) == 1:
			return self.grids[0]
		if len(self.grids) == 0:
			raise AttributeError('No grids have been defined.')
		raise AttributeError('AgDict.grid is write-only when there are multiple grids. Use AgDict.grids or AgDict.iter_grids() to access all connected grids.')
	@grid.setter
	def grid(self, val: ui.aggrid | None) -> None:
		if val:
			# if theres rows, set id
			if self.id_field:
				getRowId = f'params => params.data.{self.id_field}'  # noqa: N806
				# if getRowId in grid.options and does not match new getRowId, warn
				if ':getRowId' in val.options and val.options[':getRowId'] != getRowId:
					print('Warning: Overwriting existing :getRowId.')
				# if getRowId exists and matches new getRowId, continue
				if ':getRowId' in self.options and self.options[':getRowId'] != getRowId:
					pass
				# if getRowId does not exist, set it
				else:
					self.options[':getRowId'] = getRowId

			# update grid options with self.options, self.cols, and self.rows, TODO: update self.options on self.cols or self.rows change
			val.options = val.options | self.options | {'columnDefs': self.cols.values(), 'rowData': self.rows.values()}

			# update the grid
			val.update()
			self.grids.append(val)
			val.on('cellValueChanged', self.cell_edited)

	def cell_edited(self, e: events.GenericEventArguments) -> None:
		event = Dict(e.args)
		row = event.rowId
		col = event.colId
		id = f'{row}.{col}'
		if id in self.edit_queue:
			edit = self.edit_queue[id]
			# TODO: look into why sometimes event.oldValue != edit.old_value
			tmp = edit.old_value if edit.old_value != self.loading_sentinel else None
			if event.oldValue != tmp:
				print(f'Warning: Inconsistent old value {event.oldValue} and {tmp} in edit queue.')
			tmp = (edit.new_value if edit.new_value != self.loading_sentinel else None)
			if event.newValue != tmp:
				print(f'Warning: Inconsistent new value {event.newValue} and {tmp} in edit queue.')
				return
			del self.edit_queue[id]
		else:
			print(event)
			self.rows[row][col] = event.newValue  # update AgDict and other connected grids

	def iter_grids(self) -> Iterator[ui.aggrid]:
		self.grids[:] = [g for g in self.grids if not g.is_deleted]
		yield from self.grids
	async def check_grids_sync(self) -> None:
		'''Check that the value in cells of all connected grids is the same as in self.'''
		# wait to allow grid to process edit
		await asyncio.sleep(0.1)
		# check each grid
		for grid in self.iter_grids():
			# check rows
			data = await grid.run_grid_method('getGridOption', 'rowData')
			assert data == self.rows.values(), 'Grid rows not in sync with AgDict rows.'
			# TODO: maybe check other options

	# nicegui aggrid methods
	@overload
	def props(self, add: str | None = None, *, remove: str | None = None) -> Self: ...  # pyright: ignore[reportInconsistentOverload]
	def props(self, *args: Any, **kwargs: Any) -> Self:
		for grid in self.iter_grids():
			grid.props(*args, **kwargs)
		return self
	@overload
	def classes(self, add: str | None = None, *, remove: str | None = None, toggle: str | None = None, replace: str | None = None) -> Self: ...  # pyright: ignore[reportInconsistentOverload]
	def classes(self, *args: Any, **kwargs: Any) -> Self:
		for grid in self.iter_grids():
			grid.classes(*args, **kwargs)
		return self
	@overload
	def style(self, add: str | None = None, *, remove: str | None = None, replace: str | None = None) -> Self: ...  # pyright: ignore[reportInconsistentOverload]
	def style(self, *args: Any, **kwargs: Any) -> Self:
		for grid in self.iter_grids():
			grid.style(*args, **kwargs)
		return self
	@overload
	def on(self, type: str, handler: events.Handler[events.GenericEventArguments] | None = None, args: None | Sequence[str] | Sequence[Sequence[str] | None] = None, *, throttle: float = 0.0, leading_events: bool = True, trailing_events: bool = True, js_handler: str = '(...args) => emit(...args)') -> Self:  ...  # pyright: ignore[reportInconsistentOverload] # pylint: disable=redefined-builtin,R0913
	def on(self, *args: Any, **kwargs: Any) -> Self:
		for grid in self.iter_grids():
			grid.on(*args, **kwargs)
		return self
	def update(self) -> None:
		'''Update all connected grids.'''
		for grid in self.iter_grids():
			# update grid options with self.options, self.cols, and self.rows, TODO: update self.options on self.cols or self.rows change
			grid.options = grid.options | self.options | {'columnDefs': self.cols.values(), 'rowData': self.rows.values()}
			grid.update()
	def from_pandas(self, df: 'pd.DataFrame') -> None:  # pyright: ignore[reportUndefinedVariable] # noqa: F821
		'''Replace rows and columns from a Pandas DataFrame.

		Note:
		If the DataFrame contains non-serializable columns of type ``datetime64[ns]``, ``timedelta64[ns]``, ``complex128`` or ``period[M]``,
		they will be converted to strings.
		To use a different conversion, convert the DataFrame manually before passing it to this method.
		See `issue 1698 <https://github.com/zauberzeug/nicegui/issues/1698>`_ for more information.

		:param df: Pandas DataFrame

		'''
		import pandas as pd  # noqa: PLC0415

		def is_special_dtype(dtype) -> bool:
			return (
				pd.api.types.is_datetime64_any_dtype(dtype) or
				pd.api.types.is_timedelta64_dtype(dtype) or
				pd.api.types.is_complex_dtype(dtype) or
				isinstance(dtype, pd.PeriodDtype)
			)
		special_cols = df.columns[df.dtypes.apply(is_special_dtype)]
		if not special_cols.empty:
			df = df.copy()
			df[special_cols] = df[special_cols].astype(str)

		if isinstance(df.columns, pd.MultiIndex):
			raise ValueError(  # noqa: TRY004
				'MultiIndex columns are not supported. '
				'You can convert them to strings using something like '
				'`df.columns = ["_".join(col) for col in df.columns.values]`.'  # noqa: COM812
			)

		self.cols = [{'field': str(col)} for col in df.columns]
		self.rows = df.to_dict('records')  # pyright: ignore[reportAttributeAccessIssue]
	def from_polars(self, df: 'pl.DataFrame') -> None:  # pyright: ignore[reportUndefinedVariable] # noqa: F821
		'''Create an AG Grid from a Polars DataFrame.

		If the DataFrame contains non-UTF-8 datatypes, they will be converted to strings.
		To use a different conversion, convert the DataFrame manually before passing it to this method.

		:param df: Polars DataFrame

		'''
		self.cols = [{'field': str(col)} for col in df.columns]
		self.rows = df.to_dicts()  # pyright: ignore[reportAttributeAccessIssue]

class _AgCols(Dict, ABC, protected_attrs={'agdict', 'grids'}):  # @overload
	# def __new__(cls, cols: list | None, agdict: AgDict, **_) -> Self: ...  # pyright: ignore[reportNoOverloadImplementation, reportInconsistentOverload] pylint: disable=signature-differs
	def __init__(self, cols: list | tuple | None, agdict: AgDict, **_) -> None:
		self.grids: Callable = agdict.iter_grids
		super().__init__({col['field']: col for col in (cols or [])}, _create=True, _converter=_AgCol)
		self.agdict = agdict  # this being set indicates that grid has been initialised
	def _warn(): ...
	def values(self):  # pyright: ignore[reportIncompatibleMethodOverride]
		return [dict(val) for val in super().values()]
class _AgCol(Dict):
	def _warn(): ...


_AgCols.register(_AgCol)


class _AgRows(Dict, ABC, protected_attrs={'agdict', 'grids', 'id_field', '_id_field', 'edit_queue'}):
	def __init__(self, rows: list | tuple | None, agdict: AgDict, id_field: str) -> None:
		'Gets called by `AgDict.__init__` or user doing `agdict.rows = [...]`.'
		self.grids: Callable[[], Iterator[ui.aggrid]] = agdict.iter_grids
		self.id_field = id_field

		if id_field == '__index':
			for i, row in enumerate(rows or []):
				if '__index' in row:
					print('Warning: Overwriting existing __index field.')
				row['__index'] = str(i)
		self.update({row[id_field]: row for row in (rows or [])})

		super().__init__(
			{row[self.id_field]: row for row in (rows or [])}, _create=True,
			_converter=wrap(_AgRow, agrows=self, id_field=id_field, edit_queue=agdict.edit_queue, grids=self.grids),
		)
		self.agdict = agdict  # this being set indicates that grid has been initialised
	def __getitem__(self, key: Any) -> Any:
		if isinstance(key, int):
			key = str(key)
		return super().__getitem__(key)
	def __setitem__(self, key: Any, val: Any) -> None:
		'For when user does `agdict.rows[row] = {...}`. Add or update row in all connected grids.'
		# if user does not specify id value in `val`, set it to the key
		if self.id_field not in val:
			val[self.id_field] = key
		if key != val[self.id_field]:
			print(f'Warning: key {key} does not match id_field value {val[self.id_field]}')
		if 'agdict' in self.__dict__:  # if the rows are being initialized, skip this
			for grid in self.grids():
				grid.run_grid_method('applyTransaction', {'add': [val]})
		super().__setitem__(key, val)
	def __iadd__(self, other: list | dict) -> Self:
		'For when user does `agdict.rows += [{...}, ...]` or `agdict.rows += {...}`. Add row(s) to all connected grids.'
		if isinstance(other, list):
			for row in other:
				self[row[self.id_field]] = row
		else:  # dict
			self[other[self.id_field]] = other
		return self
	def __delitem__(self, key: Any) -> None:
		'For when user does `del agdict.rows[row]`. Delete row from all connected grids.'
		for grid in self.grids():
			grid.run_grid_method('applyTransaction', {'remove': [self[key]]})
		super().__delitem__(key)

	@property
	def id_field(self) -> str:
		return self._id_field
	@id_field.setter
	def id_field(self, val: str) -> None:
		if '_id_field' in self.__dict__:
			print('Warning: Changing id_field after rows have been initialised has not been implemented.')
		self._id_field = val

	def _warn(): ...
	def values(self) -> list[dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
		return [dict(val) for val in super().values()]
class _AgRow(Dict, protected_attrs={'agrows', 'grids', 'id', 'edit_queue'}):
	def __init__(self, row: dict, agrows: _AgRows, id_field: str, edit_queue: Dict, grids: Callable[[], Iterator[ui.aggrid]]) -> None:
		super().__init__(row, _create=True)
		self.agrows = agrows
		self.id = row[id_field]
		self.edit_queue = edit_queue
		self.grids = grids  # this being set indicates that grid has been initialised
	def __setitem__(self, key: Any, val: Any) -> None:
		'For when user does `agdict.rows[row][field] = value`. Set field in all connected grids.'
		async def update_grid(grid: ui.aggrid) -> None:
			try:
				response = await grid.run_row_method(self.id, 'setDataValue', key, val)
			except TimeoutError:
				console.print(f'[grey]Debug: Timeout while setting value for row id {self.id}, field {key} to {val}.')
				return
			if response is False:
				print(f'Info: Failed to set value for row id {self.id}, field {key} to {val}.\n\tProbably column does not exist or cell value was the same.')
			elif response is None:
				print(f'Info: Failed to set value for row id {self.id}, field {key} to {val}.\n\tProbably row does not exist.')

		# if value is not changed
		if key in self and dict.__getitem__(self, key) == val:
			return

		if 'grids' in self.__dict__:
			self.edit_queue[f'{self.id}.{key}'] = Dict(id=self.id, old_value=self[key], new_value=val)
		super().__setitem__(key, val)

		if 'grids' in self.__dict__:  # if the row is being initialized, skip this
			for grid in self.grids():
				asyncio.get_running_loop().create_task(update_grid(grid))
	def __delitem__(self, key: Any) -> None:
		'For when user does `del agdict.rows[row][field]`. Delete field from all connected grids.'
		async def update_grid(grid: ui.aggrid) -> None:
			try:
				response = await grid.run_row_method(self[self.agrows.id_field], 'setDataValue', key, None)
			except TimeoutError:
				print(f'Debug: Timeout while deleting row {self.id} field {key}.')
			if response is False:
				print(f'Warning: Failed to delete value for row id {self.id}, field {key}.\n\tProbably column does not exist.')
			elif response is None:
				print(f'Warning: Failed to delete value for row id {self.id}, field {key}.\n\tProbably row does not exist.')

		if 'grids' in self.__dict__:
			self.edit_queue[f'{self.id}.{key}'] = Dict(id=self.id, old_value=self[key], new_value=None)

		for grid in self.grids():
			asyncio.get_running_loop().create_task(update_grid(grid))
		super().__delitem__(key)

	def _warn(): ...
	def _create(self) -> Self:
		return _AgRow({}, self.agrows, self.agrows.id_field, self.grids)


_AgRows.register(_AgRow)

# TODO:
#  - make sync from grid to AgDict
#  - test with complex objects, https://nicegui.io/documentation/aggrid#ag_grid_with_complex_objects
