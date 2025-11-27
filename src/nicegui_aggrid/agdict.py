from collections.abc import Callable, Iterator, Sequence
from typing import Any, Self, overload

from epicstuff import BoxDict, Dict
from nicegui import ui, events


class AgDict:
	'''A Dict that can be "connected" to multiple aggrids such that changes to this Dict will be updated in all connected aggrids without the use of aggrid.update().'''

	def __init__(
		self,
		options: dict | None = None, columns: list | tuple | None = None, rows: list | tuple | None = None,
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
		options = Dict(options, _create=True)
		if grid:
			# merge grid.options with option, options taking precedence
			options: Dict = Dict(grid.options | options, _create=True)
		# if cols not already set, get them from the grid
		# # if columns, override options
		if columns:
			options.columnDefs = columns
		# # else, get columns from options
		elif options.get('columnDefs'):
			columns = options.columnDefs
		# if rows not already set, get them from the grid
		# # if rows, override options
		if rows:
			options.rowData = rows
		# # else, get rows from options
		elif options.get('rowData'):
			rows = options.rowData

		# make aggrid use the id_field
		if ':getRowId' in options: ...  # TODO: maybe extract id_field from existing getRowId
		# enable loading skeletons if needed
		if loading:
			options.defaultColDef |= {'cellRendererSelector': "params => params.value === '__loading' ? {component: 'agSkeletonCellRenderer'} : null"}

		super().__init__()

		self.grids = []
		self._loading = loading
		self.options = options or {}  # note: does not sync with rows/cols, just gets overwritten
		self.id_field = id_field
		self.cols = columns  # gets auto converted to _AgCols
		self.rows = rows  # gets auto converted to _AgRows  # pyright: ignore[reportAttributeAccessIssue]
		self.grid = grid or (ui.aggrid(self.options, **kwargs) if create_grid else None)

	# properties
	@property
	def options(self) -> Dict:
		return self._options
	@options.setter
	def options(self, val: dict) -> None:
		self._options = Dict(val)
		if self.grids:
			for grid in self.iter_grids():
				grid.run_grid_method('updateGridOptions', val)		# if changing id_field and rows is allready set
	@property
	def id_field(self) -> str | None:
		return self._id_field
	@id_field.setter
	def id_field(self, val: str | None) -> None:
		self._id_field = val
		if hasattr(self, 'rows'):
			# set the new id_field
			for grid in self.iter_grids():
				grid.run_grid_method('setGridOption', ':getRowId', f'params => params.data.{val}')
			# reinitialize the rows with the new id_field
			self.rows = self.rows.values()  # pyright: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
			# TODO: if no id feild provided, generate random/add number "column"
	@property
	def cols(self) -> '_AgCols | None':
		return self._cols
	@cols.setter
	def cols(self, val: '_AgCols | list | tuple | None') -> None:
		# TODO
		if hasattr(self, '_cols'):
			print('Warning: changing cols after initialisation has not been implemented yet.')
			return
		if val is not None:
			val = _AgCols(val, self)  # pyright: ignore[reportArgumentType]
		self._cols = val
	@property
	def rows(self) -> '_AgRows':
		return self._rows
	@rows.setter
	def rows(self, val: '_AgRows | list | tuple | None') -> None:
		# if new rows or if called by __setitem__ with key id_field
		if not isinstance(val, _AgRows):
			if self.id_field is None:
				raise ValueError('id_field must be specified before setting rows.')
			# if no rows and loading enabled, create loading rows
			if val is None and self._loading:
				if self.cols is None:
					raise ValueError('Columns must be set to use loading.')
				val = [{col.field: '__loading' for col in self.cols}] * self._loading
			val = _AgRows(val, self, self.id_field)  # pyright: ignore[reportArgumentType]
			for grid in self.iter_grids():
				grid.run_grid_method('setGridOption', 'rowData', val.values())
		# else, called by __iadd__ from _AgRows, grid allready updated, do nothing extra
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
			if self.rows:
				getRowId = f'params => params.data.{self.id_field}'
				if (':getRowId' in val.options and val.options[':getRowId'] != getRowId) or (':getRowId' in self.options and self.options[':getRowId'] != getRowId):
					print('Warning: Overwriting existing :getRowId.')
				self.options[':getRowId'] = getRowId

			self.grids.append(val)
			val.options |= self.options
			val.update()
			# TODO: think about/look into if options should be updated on change after this point

	def iter_grids(self) -> Iterator[ui.aggrid]:
		self.grids[:] = [g for g in self.grids if not g.is_deleted]
		yield from self.grids

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

class _AgCols(BoxDict):
	_protected_keys = BoxDict._protected_keys | {'agdict', 'grids', ''}  # noqa: SLF001

	# @overload
	# def __new__(cls, cols: list | None, agdict: AgDict, **_) -> Self: ...  # pyright: ignore[reportNoOverloadImplementation, reportInconsistentOverload] pylint: disable=signature-differs
	def __init__(self, cols: list | None, agdict: AgDict, **_) -> None:
		self.grids: Callable[[], Iterator[ui.aggrid]] = agdict.iter_grids
		super().__init__(_convert=True, _create=True)
		self.cols = cols
		self.agdict = agdict  # this being set indicates that grid has been initialised
	def _do_convert(self, val: Any, **_) -> Any:  # pylint: disable=arguments-differ
		if isinstance(val, dict):
			return Dict(val)
		return super()._do_convert(val)
	def values(self):  # pyright: ignore[reportIncompatibleMethodOverride]
		return [] if self.cols is None else [dict(val) for val in self.cols]

class _AgRows(BoxDict):
	_protected_keys = BoxDict._protected_keys | {'agdict', 'grids', 'id_field'}  # noqa: SLF001

	# @overload
	# def __new__(cls, _map: list | tuple | None, agdict: AgDict, id_field: str) -> Self: ...  # pyright: ignore[reportNoOverloadImplementation, reportInconsistentOverload] pylint: disable=signature-differs
	def __init__(self, _map: list | tuple | None, agdict: AgDict, id_field: str) -> None:
		self.grids: Callable[[], Iterator[ui.aggrid]] = agdict.iter_grids
		self.id_field = id_field
		super().__init__(self._do_convert(_map), _convert=True, _create=True)
		self.agdict = agdict  # this being set indicates that grid has been initialised
	def __setitem__(self, key: Any, val: Any) -> None:
		'For when user does `agdict.rows[row] = {...}`. Add or update row in all connected grids.'
		# if user does not specify id value in `val`, set it to the key
		if self.id_field not in val:
			val[self.id_field] = key
		if key != val[self.id_field]:
			print(f'Warning: key {key} does not match id_field value {val[self.id_field]}')
		if self.hasattr('agdict'):  # if the rows are being initialized, skip this
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

	def values(self) -> list[dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
		return [dict(val) for val in super().values()]
	def _do_convert(self, val: Any, **_) -> Any:  # pylint: disable=arguments-differ
		if isinstance(val, list):
			return {row[self.id_field]: row for row in super()._do_convert(val)}
		if isinstance(val, dict) and not isinstance(val, _AgRow):
			return _AgRow(val, self, self.grids)
		return val
class _AgRow(BoxDict):
	_protected_keys = BoxDict._protected_keys | {'agrows', 'grids'}  # noqa: SLF001
	def __init__(self, _map: dict, agrows: _AgRows, grids: Callable[[], Iterator[ui.aggrid]]) -> None:
		super().__init__(_map, _create=True)
		self.grids = grids  # this being set indicates that grid has been initialised
		self.agrows = agrows
	def __setitem__(self, key: Any, val: Any) -> None:
		'For when user does `agdict.rows[row][field] = value`. Set field in all connected grids.'
		super().__setitem__(key, val)
		if self.hasattr('grids'):  # if the row is being initialized, skip this
			for grid in self.grids():
				grid.run_row_method(self[self.agrows.id_field], 'setDataValue', key, val)
	def __delitem__(self, key: Any) -> None:
		'For when user does `del agdict.rows[row][field]`. Delete field from all connected grids.'
		for grid in self.grids():
			grid.run_row_method(self[self.agrows.id_field], 'setDataValue', key, None)
		super().__delitem__(key)

	def _create(self):
		return _AgRow({}, self.agrows, self.grids)
# TODO:
#  - make sync from grid to AgDict
#  - test with complex objects, https://nicegui.io/documentation/aggrid#ag_grid_with_complex_objects
