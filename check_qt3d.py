import importlib.util
modules = ['PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DExtras', 'PySide6.Qt3DInput', 'cadquery']
for module in modules:
    spec = importlib.util.find_spec(module)
    print(module, '✓' if spec else '✗')
