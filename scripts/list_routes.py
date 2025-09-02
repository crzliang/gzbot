import nonebot
import inspect


def dump_routes(app, prefix=''):
    # Try Starlette/ASGI-app style
    routes = getattr(app, 'routes', None)
    if routes:
        for r in routes:
            p = getattr(r, 'path', None) or getattr(r, 'prefix', None) or None
            print(prefix, type(r).__name__, p, r)
    # If mounted apps exist, try to inspect children
    mounts = []
    for name, val in inspect.getmembers(app):
        if name.startswith('_'):
            continue
        if hasattr(val, 'routes') and val is not app:
            mounts.append((name, val))
    for name, a in mounts:
        dump_routes(a, prefix=prefix + name + '.')


nonebot.init()
nonebot.load_plugins('bot')
app = nonebot.get_asgi()

print('Inspecting ASGI app:')
dump_routes(app)
