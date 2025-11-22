from pathlib import Path

from epicstuff import s
from nicegui import app, ui


_shim_created = False

def jailbreak(shim_dir: str | Path | None = None):
	global _shim_created

	shim_dir = shim_dir or Path('.nicegui') / 'aggrid_shim'
	shim_dir = Path(shim_dir)
	if not _shim_created:
		# put the shim wherever you like in your repo
		shim_dir.mkdir(exist_ok=True)
		(shim_dir / 'index.js').write_text(s('''
			const g = window.agGrid
			export default {
				createGrid: g.createGrid,
				themes: {
					alpine: g.themeAlpine,
					balham: g.themeBalham,
					material: g.themeMaterial,
					quartz: g.themeQuartz,
				},
				colorSchemeVariable: g.colorSchemeVariable,
			}
		''').str, encoding='utf-8')
		_shim_created = True

	app.add_static_files('/aggrid-shim', str(shim_dir))
	ui.add_head_html(s('''
		<script src="https://cdn.jsdelivr.net/npm/ag-grid-enterprise@34.3.1/dist/ag-grid-enterprise.min.js"></script>
		<script type="importmap">
		{
			"imports": {
				"nicegui-aggrid": "/aggrid-shim/index.js"
			}
		}
		</script>
	''').str)
