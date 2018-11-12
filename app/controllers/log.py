import json
import uuid

from aiohttp import web
from multidict import istr

from app import models as m
from app import helper
from app.utils.aiohttp_controller import Controller

logger = helper.logger

RUN_CODE_MAX_OUTPUT = 1 * 1024 * 1024  # 1 MB
RUN_CODE_MAX_TTL = 5 * 60  # 5 min
RUN_CODE_MAX_MEMORY = 256 * 1024 * 1024  # 256 MB

controller = Controller('log')


@controller.route('/log/ticket', 'POST')
async def log_ticket(request):
    user_agent = request.headers.get(istr('USER-AGENT'))
    referer = request.headers.get(istr('REFERER'))

    if user_agent is None:
        user_agent = ''

    if referer is None:
        referer = ''

    post_data = await request.post()

    try:
        name = post_data['name']
    except KeyError:
        return web.HTTPBadRequest()

    if not 1 <= len(name) <= 64:
        return web.HTTPBadRequest(text='name -- Invalid string format (1~64)')

    with request.app['db']() as session:
        log_ticket = m.LogTicket(
            ticket=str(uuid.uuid4()),
            ip=request.remote,
            user_agent=user_agent,
            referer=referer,
            name=name
        )

        session.add(log_ticket)

        return web.json_response({
            'ticket': log_ticket.ticket
        })


@controller.route('/log/submit', 'POST')
async def log_submit(request):
    post_data = await request.post()

    try:
        ticket = post_data['ticket']
        data = post_data['data']
    except KeyError:
        return web.HTTPBadRequest()

    if len(ticket) != 36:
        return web.HTTPBadRequest(text='ticket -- Invalid string format (36~36)')

    try:
        json.loads(data)
    except ValueError:
        return web.HTTPBadRequest(text='data -- Invliad json format')

    with request.app['db']() as session:
        log_ticket = session \
            .query(m.LogTicket) \
            .filter(m.LogTicket.ticket == ticket) \
            .first()

        if log_ticket is None:
            return web.HTTPNotFound(text='ticket -- Not exist')

        log_entry = m.LogEntry(
            log_ticket=log_ticket,
            data=data
        )

        session.add(log_entry)

        return web.json_response({})
