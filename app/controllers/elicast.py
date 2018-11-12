import json

from aiohttp import web

from app import models as m
from app import helper
from app.utils.aiohttp_controller import Controller

config = helper.config

WEBM_BASE64_HEADER = 'data:audio/webm;base64'

controller = Controller('elicast')


@controller.route('/elicast', 'GET')
async def elicast_list(request):
    try:
        page = int(request.query.get('page', 0))
        count = int(request.query.get('count', 20))
        teacher = request.query.get('teacher')
        if not teacher:
            teacher = None
    except ValueError:
        return web.HTTPBadRequest()

    if not 0 <= page:
        return web.HTTPBadRequest(text='page -- Invalid int format (0~)')

    if not 1 <= count <= 100:
        return web.HTTPBadRequest(text='count -- Invalid int format (1~100)')

    if not (teacher is None or (isinstance(teacher, str) and 1 <= len(teacher) <= 64)):
        return web.HTTPBadRequest(text='teacher -- should be null or str format (length 1~64)')

    with request.app['db']() as session:
        elicasts = session \
            .query(m.Elicast) \
            .filter(
                (m.Elicast.teacher == teacher) &
                ~m.Elicast.is_deleted
            ) \
            .order_by(m.Elicast.created.desc()) \
            .offset(count * page) \
            .limit(count)

        elicasts_json = []
        for elicast in elicasts:
            elicasts_json.append({
                'id': elicast.id,
                'created': elicast.created,
                'title': elicast.title,
                'teacher': elicast.teacher,
                'is_protected': elicast.is_protected
            })

        return web.json_response({
            'elicasts': elicasts_json
        })


@controller.route('/elicast', 'PUT')
async def elicast_put(request):
    if config.IS_EDIT_BLOCKED:
        return web.HTTPForbidden()

    return await eliceast_put_or_post(request, None)


@controller.route('/elicast/{elicast_id:[1-9]+\d*}', 'POST')
async def elicast_post(request):
    if config.IS_EDIT_BLOCKED:
        return web.HTTPForbidden()

    elicast_id = request.match_info['elicast_id']
    return await eliceast_put_or_post(request, elicast_id)


async def eliceast_put_or_post(request, elicast_id):
    # TODO : vulnerable to OOM
    post_data = await request.post()

    try:
        title = post_data['title']
        ots_str = post_data['ots']
        voice_blobs_str = post_data['voice_blobs']
        teacher = post_data.get('teacher')
        if not teacher:
            teacher = None
    except KeyError:
        return web.HTTPBadRequest()

    if not 1 <= len(title) <= 128:
        return web.HTTPBadRequest(text='title -- Invalid str format (length 1~128)')

    try:
        ots = json.loads(ots_str)
        if not isinstance(ots, list):
            raise ValueError()
        # TODO : ot validation
    except ValueError:
        return web.HTTPBadRequest(text='ots -- Invliad json format')

    try:
        voice_blobs = json.loads(voice_blobs_str)
        if not isinstance(voice_blobs, list):
            raise ValueError()

        for voice_blob in voice_blobs:
            mtype, voice_data_base64 = voice_blob.split(',')
            if mtype != WEBM_BASE64_HEADER:
                return web.HTTPBadRequest(text='voice_blobs -- only support audio/webm')
    except ValueError:
        return web.HTTPBadRequest(text='voice_blobs -- Invliad json format')

    if not (teacher is None or (isinstance(teacher, str) and 1 <= len(teacher) <= 64)):
        return web.HTTPBadRequest(text='teacher -- should be null or str format (length 1~64)')

    with request.app['db']() as session:
        if elicast_id is None:
            elicast = m.Elicast(
                title=title,
                ots=ots_str,
                voice_blobs=voice_blobs_str,
                teacher=teacher
            )
        else:
            elicast = session \
                .query(m.Elicast) \
                .filter(
                    (m.Elicast.id == elicast_id) &
                    ~m.Elicast.is_deleted &
                    ~m.Elicast.is_protected
                ) \
                .first()

            if elicast is None:
                return web.HTTPNotFound(text='elicast -- Not exist')

            elicast.title = title
            elicast.ots = ots_str
            elicast.voice_blobs = voice_blobs_str
            elicast.teacher = teacher

        session.add(elicast)

        session.flush()

        return web.json_response({
            'elicast': {
                'id': elicast.id
            }
        })


@controller.route('/elicast/{elicast_id:[1-9]+\d*}', 'GET')
async def elicast_get(request):
    elicast_id = request.match_info['elicast_id']

    with request.app['db']() as session:
        elicast = session \
            .query(m.Elicast) \
            .filter(
                (m.Elicast.id == elicast_id) &
                ~m.Elicast.is_deleted
            ) \
            .first()

        if elicast is None:
            return web.HTTPNotFound(text='elicast -- Not exist')

        elicast_json = {
            'id': elicast.id,
            'created': elicast.created,
            'title': elicast.title,
            'ots': json.loads(elicast.ots),
            'voice_blobs': json.loads(elicast.voice_blobs),
            'teacher': elicast.teacher,
            'is_protected': elicast.is_protected
        }

        return web.json_response({
            'elicast': elicast_json
        })


@controller.route('/elicast/{elicast_id:[1-9]+\d*}', 'DELETE')
async def elicast_delete(request):
    if config.IS_EDIT_BLOCKED:
        return web.HTTPForbidden()

    elicast_id = request.match_info['elicast_id']

    with request.app['db']() as session:
        elicast = session \
            .query(m.Elicast) \
            .filter(
                (m.Elicast.id == elicast_id) &
                ~m.Elicast.is_deleted &
                ~m.Elicast.is_protected
            ) \
            .first()

        if elicast is None:
            return web.HTTPNotFound(text='elicast -- Not exist')

        elicast.is_deleted = True
        session.add(elicast)

        return web.json_response({})
