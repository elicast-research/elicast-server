import asyncio

from app import Webserver

try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

if __name__ == '__main__':
    if UVLOOP_AVAILABLE:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    webserver = Webserver()
    webserver.prepare()
    webserver.run()
else:
    webserver = Webserver()
    webserver.prepare()
