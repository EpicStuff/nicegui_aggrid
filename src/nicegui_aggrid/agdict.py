from collections.abc import Callable, Iterator
from typing import Any, Self

from epicstuff import Dict
from nicegui import ui


# serve the folder at a fixed url


class AgDict:
	'''A Dict that can be "connected" to multiple aggrids such that changes to this Dict will be updated in all connected aggrids without the use of aggrid.update().'''

	def __init__(
		self, *,
		columns: list | tuple | None = None, rows: list | tuple | None = None, grid: ui.aggrid | None = None,
		id_field: str | None = None, loading: int = 1,
	) -> None:
		'''Initialize an AgDict instance.

		:param columns: List or tuple of column definitions. What would normally be in options["columnDefs"].
		:param rows: List or tuple of row data. What would normally be in options["rowData"].
		:param grid: An optional NiceGUI aggrid instance to connect to this AgDict. Can be added latter with the `grid` attribute.
		:param id_field: The field to use as the unique identifier for rows.
		:param loading: Number of loading skeleton rows to show when no rows are provided.
		'''
		super().__init__()
		self.grids = []
		self._enable_loading = loading
		self.cols: Dict | list | tuple | None = columns
		self.id_field = id_field
		self.rows: _AgRows | list | tuple | None = rows  # pyright: ignore[reportAttributeAccessIssue]
		self.grid: ui.aggrid | None = grid
	def __setattr__(self, key: Any, val: Any) -> None:  # noqa: C901
		if key == 'grid':
			if val:
				self.grids.append(val)
				val.options['columnDefs'] = self.cols
				val.options['rowData'] = self.rows.values()  # pyright: ignore[reportAttributeAccessIssue]
				val.options[':getRowId'] = f'params => params.data.{self.id_field}'
				# if self.is_loading:
				# 	val.options['defaultColDef'] = {'cellRenderer': 'agSkeletonCellRenderer'}
				val.update()
				# TODO: think about/look into if options should be updated on change after this point
			return
		if key == 'rows':
			# if new rows or if called by __setitem__ with key id_field
			if not isinstance(val, _AgRows):
				if self.id_field is None:
					raise ValueError('id_field must be specified before setting rows.')
				# if no rows
				if val is None:
					if self.cols is None:
						raise ValueError('Columns must be set to use loading.')
					val = [{col.field: '__loading' for col in self.cols}] * self._enable_loading
				val = _AgRows(val, self, self.id_field)
				for grid in self.iter_grids():
					grid.run_grid_method('setGridOption', 'rowData', val.values())
			# else, called by __iadd__ from _AgRows, grid allready updated, do nothing extra
		elif key == 'cols':  # TODO
			if hasattr(self, 'cols'):
				print('Warning: changing cols after initialisation has not been implemented yet.')
				return
			val = list(map(Dict, val))
		# if changing id_field and rows is allready set
		elif key == 'id_field' and hasattr(self, 'rows'):
			# set the new id_field
			for grid in self.iter_grids():
				grid.run_grid_method('setGridOption', ':getRowId', f'params => params.data.{val}')
			super().__setattr__(key, val)
			# reinitialize the rows with the new id_field
			self.rows = self.rows.values()  # pyright: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
			return
			# TODO: if no id feild provided, generate random/add number "column"

		super().__setattr__(key, val)
	def __getattr__(self, key: Any) -> Any:
		if key == 'grid':
			if len(self.grids) == 1:
				return self.grids[0]
			if len(self.grids) == 0:
				raise AttributeError('No grids have been defined.')
			raise AttributeError('AgDict.grid is write-only when there are multiple grids. Use AgDict.grids or AgDict.iter_grids() to access all connected grids.')
		return super().__getattribute__(key)

	def iter_grids(self) -> Iterator[ui.aggrid]:
		self.grids[:] = [g for g in self.grids if not g.is_deleted]
		yield from self.grids

	def from_pandas(self, df: 'pd.DataFrame'):  # pyright: ignore[reportUndefinedVariable] # noqa: F821
		'''Replace rows and columns from a Pandas DataFrame.

		Note:
		If the DataFrame contains non-serializable columns of type ``datetime64[ns]``, ``timedelta64[ns]``, ``complex128`` or ``period[M]``,
		they will be converted to strings.
		To use a different conversion, convert the DataFrame manually before passing it to this method.
		See `issue 1698 <https://github.com/zauberzeug/nicegui/issues/1698>`_ for more information.

		:param df: Pandas DataFrame

		'''
		import pandas as pd  # noqa: PLC0415

		def is_special_dtype(dtype):
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
	def from_polars(self, df: 'pl.DataFrame'):  # pyright: ignore[reportUndefinedVariable] # noqa: F821
		'''Create an AG Grid from a Polars DataFrame.

		If the DataFrame contains non-UTF-8 datatypes, they will be converted to strings.
		To use a different conversion, convert the DataFrame manually before passing it to this method.

		:param df: Polars DataFrame

		'''
		self.cols = [{'field': str(col)} for col in df.columns]
		self.rows = df.to_dicts()  # pyright: ignore[reportAttributeAccessIssue]

class _AgRows(Dict):
	_protected_keys = Dict._protected_keys | {'agdict', 'grids', 'id_field'}  # noqa: SLF001

	def __init__(self, _map: list | None, agdict: AgDict, id_field: str) -> None:
		self.grids: Callable[[], Iterator[ui.aggrid]] = agdict.iter_grids
		self.id_field = id_field
		super().__init__(self._do_convert(_map), _convert=True, _create=True)
		self.agdict = agdict  # this being set indicates that grid has been initialised
	def __setitem__(self, key: Any, val: Any) -> None:
		# if user does not specify id value, set it to the key
		if self.id_field not in val:
			val[self.id_field] = key
		if key != val[self.id_field]:
			print(f'Warning: key {key} does not match id_field value {val[self.id_field]}')
		if hasattr(self, 'agdict'):  # if the rows are being initialized, skip this
			for grid in self.grids():
				grid.run_grid_method('applyTransaction', {'add': [val]})
		super().__setitem__(key, val)
	def __iadd__(self, other) -> Self:
		self[other[self.id_field]] = other
		return self
	def __delitem__(self, key: Any) -> None:
		for grid in self.grids():
			grid.run_grid_method('applyTransaction', {'remove': [self[key]]})
		super().__delitem__(key)

	def values(self):  # pyright: ignore[reportIncompatibleMethodOverride]
		return [dict(val) for val in super().values()]
	def _do_convert(self, val: Any, **_) -> Any:  # pylint: disable=arguments-differ
		if isinstance(val, list):
			return {row[self.id_field]: row for row in super()._do_convert(val)}
		if isinstance(val, dict) and not isinstance(val, _AgRow):
			return _AgRow(val, self, self.grids)
		return val

class _AgRow(Dict):
	_protected_keys = Dict._protected_keys | {'agrows', 'grids'}  # noqa: SLF001
	def __init__(self, _map: dict, agrows: _AgRows, grids: Callable[[], Iterator[ui.aggrid]]) -> None:
		super().__init__(_map, _create=True)
		self.grids = grids  # this being set indicates that grid has been initialised
		self.agrows = agrows
	def __setitem__(self, key: Any, val: Any) -> None:
		super().__setitem__(key, val)
		if hasattr(self, 'grids'):  # if the row is being initialized, skip this
			for grid in self.grids():
				grid.run_row_method(self[self.agrows.id_field], 'setDataValue', key, val)
	def __delitem__(self, key: Any) -> None:
		for grid in self.grids():
			grid.run_row_method(self[self.agrows.id_field], 'setDataValue', key, None)
		super().__delitem__(key)

# TODO:
#  - make sync from grid to AgDict
#  - test with complex objects, https://nicegui.io/documentation/aggrid#ag_grid_with_complex_objects
