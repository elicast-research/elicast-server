import collections
import functools

from aiohttp import web

_ALLOWED_METHODS = set(['OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'])


class Controller:

    def __init__(self, name):
        self.name = name

        self._routes = collections.defaultdict(dict)

    async def default_options_route(self, allow_header, request):
        return web.Response(
            text='',
            headers={
                'Allow': allow_header
            }
        )

    def route(self, path, method):
        def _wrapper(f):
            @functools.wraps(f)
            def _wrapped(*args, **kwargs):
                return f(*args, **kwargs)

            if method not in _ALLOWED_METHODS:
                raise Exception('Unsupported method', method)

            if method in self._routes[path]:
                raise Exception('Already registered route', self._routes[path][method])

            self._routes[path][method] = f

            return _wrapped
        return _wrapper

    def register(self, app):
        for path, method_handler_dict in self._routes.items():
            for method, handler in method_handler_dict.items():
                app.router.add_route(method, path, handler)

            if 'OPTIONS' not in method_handler_dict:
                allow_methods = list(method_handler_dict.keys())
                allow_methods.append('OPTIONS')
                app.router.add_route(
                    'OPTIONS',
                    path,
                    functools.partial(self.default_options_route,
                                      ', '.join(allow_methods))
                )
