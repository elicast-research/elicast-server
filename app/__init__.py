import asyncio
import concurrent.futures

import aiohttp.web
import docker
import sqlalchemy as sa

from . import controllers, helper, models

config = helper.config
logger = helper.logger


class Webserver(object):

    def __init__(self):
        self.app = None

        self._loop = asyncio.get_event_loop()

    def prepare(self):
        helper.init_logger(logger)

        self._loop.run_until_complete(self._prepare())

    async def _prepare(self):
        app = self.app = aiohttp.web.Application(
            client_max_size=100 * 1024 ** 2
        )

        app.on_startup.append(self.startup)
        app.on_cleanup.append(self.cleanup)
        app.on_response_prepare.append(self.response_prepare)

        for controller in controllers.AVAILABLE_CONTROLLERS:
            controller.register(app)

    def run(self):
        try:
            aiohttp.web.run_app(self.app,
                                host='0.0.0.0',
                                port=7822)
        except Exception:
            logger.exception('Failed to run webserver.')

    async def startup(self, app):
        engine = sa.create_engine(config.DB_URI)
        models.Base.metadata.create_all(engine)

        models.Session.configure(bind=engine)
        app['db'] = models.SessionContext

        app['docker'] = docker.DockerClient(base_url=config.DOCKER_URI)

        app['executor'] = concurrent.futures.ThreadPoolExecutor(200)

    async def cleanup(self, app):
        models.Session.remove()

    async def response_prepare(self, request, response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, PUT, DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
