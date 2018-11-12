import asyncio
import json
import tempfile

from aiohttp import web

from app import models as m
from app import helper
from app.utils.aiohttp_controller import Controller

logger = helper.logger

RUN_CODE_MAX_OUTPUT = 1 * 1024 * 1024  # 1 MB
RUN_CODE_MAX_TTL = 5 * 60  # 5 min
RUN_CODE_MAX_MEMORY = 256 * 1024 * 1024  # 256 MB

controller = Controller('code')


async def _run_code(app, code):
    container_output = ''
    container_exit_code = -1

    with tempfile.NamedTemporaryFile() as codefile:
        codefile.write(code.encode('utf-8'))
        codefile.flush()

        container = app['docker'].containers.run(
            'python:3.6',
            'python -u /codefile.py',
            detach=True,
            log_config={
                'type': 'json-file',
                'config': {
                    'max-size': str(RUN_CODE_MAX_OUTPUT)
                }
            },
            mem_limit=RUN_CODE_MAX_MEMORY,
            network='none',
            stdout=True,
            stderr=True,
            volumes={
                codefile.name: {
                    'bind': '/codefile.py',
                    'mode': 'ro'
                }
            }
        )

        try:
            loop = asyncio.get_event_loop()

            try:
                is_timeout = False
                container_exit_code = (await asyncio.wait_for(
                    loop.run_in_executor(app['executor'], container.wait),
                    timeout=RUN_CODE_MAX_TTL
                ))['StatusCode']
            except asyncio.TimeoutError:
                logger.warn('Code run TIMEOUT')
                is_timeout = True
                container_exit_code = -1

            container_output = container.logs().decode('utf-8', 'replace')

            if is_timeout:
                container_output += '\n<TIMEOUT>'

        finally:
            container.remove(force=True)

    return container_output, container_exit_code


@controller.route('/code/run', 'POST')
async def code_run(request):
    post_data = await request.post()

    try:
        code = post_data['code']
    except KeyError:
        return web.HTTPBadRequest()

    with request.app['db']() as session:
        container_output, container_exit_code = await _run_code(request.app, code)

        code_run = m.CodeRun(
            code=code,
            output=container_output,
            exit_code=container_exit_code
        )

        session.add(code_run)

        session.flush()

        return web.json_response({
            'code_run': {
                'id': code_run.id,
            },
            'output': container_output,
            'exit_code': container_exit_code
        })


@controller.route('/code/answer/{elicast_id:[1-9]+\d*}', 'POST')
async def code_answer(request):
    elicast_id = request.match_info['elicast_id']

    post_data = await request.post()

    try:
        ex_id = post_data['ex_id']
        solve_ots_str = post_data['solve_ots']
        code = post_data['code']
    except KeyError:
        return web.HTTPBadRequest()

    try:
        solve_ots = json.loads(solve_ots_str)
        if not isinstance(solve_ots, list):
            raise ValueError()
        # TODO : ot validation
    except ValueError:
        return web.HTTPBadRequest(text='solve_ots -- Invliad json format')

    with request.app['db']() as session:
        elicast = session \
            .query(m.Elicast) \
            .filter(m.Elicast.id == elicast_id) \
            .first()

        if elicast is None:
            return web.HTTPNotFound(text='elicast -- Not exist')

        container_output, container_exit_code = await _run_code(request.app, code)

        code_run_exercise = m.CodeRunExercise(
            elicast=elicast,
            ex_id=ex_id,
            solve_ots=json.dumps(solve_ots),
            code=code,
            output=container_output,
            exit_code=container_exit_code
        )

        session.add(code_run_exercise)

        session.flush()

        return web.json_response({
            'code_run_exercise': {
                'id': code_run_exercise.id
            },
            'exit_code': container_exit_code
        })
