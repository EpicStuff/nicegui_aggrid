from pathlib import Path

from epicstuff import s
from nicegui import app, ui


_shim_created = False

def enterprise(shim_dir: str | Path | None = None, aggrid_js_path: str | Path | None = None, license_key: str | None = None) -> None:
	global _shim_created

	shim_dir = shim_dir or Path('.nicegui') / 'aggrid_shim'
	shim_dir = Path(shim_dir)
	if not _shim_created:
		# put the shim wherever you like in your repo
		shim_dir.mkdir(parents=True, exist_ok=True)
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

	# default to CDN if no custom path provided
	js_path = 'https://cdn.jsdelivr.net/npm/ag-grid-enterprise@34.3.1/dist/ag-grid-enterprise.min.js'
	if aggrid_js_path:
		aggrid_js_path = Path(aggrid_js_path)
		# serve the provided JS file via NiceGUI static files
		app.add_static_files('/aggrid-enterprise', str(aggrid_js_path.parent))
		js_path = f'/aggrid-enterprise/{aggrid_js_path.name}'

	app.add_static_files('/aggrid-shim', str(shim_dir))
	license_script = ''
	if license_key:
		license_script = f'<script>window.agGrid?.LicenseManager?.setLicenseKey({license_key})</script>'
	ui.add_head_html(s(f'''
		<script src="{js_path}"></script>{license_script}
		{license_script}
		<script type="importmap">
		{{
			"imports": {{
				"nicegui-aggrid": "/aggrid-shim/index.js"
			}}
		}}
		</script>
	''').str)
