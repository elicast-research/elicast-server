import asyncio
import base64
import io
import json
import os.path
import subprocess
import tarfile
import tempfile

import aiohttp
from aiohttp import web

from app import models as m
from app import helper
from app.utils.aiohttp_controller import Controller

config = helper.config
logger = helper.logger

WEBM_BASE64_HEADER = 'data:audio/webm;base64'
FFMPEG_ENCODE_TIMEOUT = 60

controller = Controller('audio')


def _any_audio_to_webm(source_f, target_f):
    ffmpeg_run = subprocess.run(
        [
            '/usr/bin/ffmpeg',
            '-i', source_f.name,  # input filename
            '-acodec', 'copy',  # avoid re-encoding
            '-y',  # overwrite file
            target_f.name  # output filename
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=FFMPEG_ENCODE_TIMEOUT
    )

    if ffmpeg_run.returncode != 0:
        logger.warn(ffmpeg_run.stdout.decode('utf-8'))
    else:
        logger.debug(ffmpeg_run.stdout.decode('utf-8'))


def _fix_chrome_webm(source_f, target_f):
    # Fix for Chrome bug https://bugs.chromium.org/p/chromium/issues/detail?id=642012
    return _any_audio_to_webm(source_f, target_f)


def _split_audio(source_data_list, segments):
    source_f_list = []
    for source_data in source_data_list:
        source_f = tempfile.NamedTemporaryFile(suffix='.webm')
        with tempfile.NamedTemporaryFile(suffix='.webm') as source_buggy_f:
            source_buggy_f.write(source_data)
            source_buggy_f.flush()
            _fix_chrome_webm(source_buggy_f, source_f)

        source_f_list.append(source_f)

    with tempfile.NamedTemporaryFile(suffix='.txt', mode='w+b') as fielist_f:
        fielist_f.write(
            '\n'.join("file '%s'" % source_f.name
                      for source_f in source_f_list)
            .encode('utf-8')
        )
        fielist_f.flush()

        outputs = []
        for start_ts, end_ts in segments:
            with tempfile.NamedTemporaryFile(suffix='.webm') as output_f:
                try:
                    ffmpeg_run = subprocess.run(
                        [
                            '/usr/bin/ffmpeg',
                            '-f', 'concat',
                            '-safe', '0',  # for concat on absolute path
                            '-i', fielist_f.name,  # input filename
                            '-ss', str(start_ts / 1000),  # audio start position
                            '-t', str((end_ts - start_ts) / 1000),  # audio length
                            '-acodec', 'copy',  # avoid re-encoding (seeking on iframe -> not accurate)
                            '-y',  # overwrite file
                            output_f.name  # output filename
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=FFMPEG_ENCODE_TIMEOUT
                    )
                except Exception:
                    logger.exception('Failed to call ffmpeg')
                    break

                if ffmpeg_run.returncode != 0:
                    logger.warn(ffmpeg_run.stdout.decode('utf-8'))
                else:
                    logger.debug(ffmpeg_run.stdout.decode('utf-8'))

                outputs.append(output_f.read())

    for source_f in source_f_list:
        source_f.close()

    return outputs


def _add_to_tarfile(tf, filename, content):
    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
    else:
        content_bytes = content
    tarinfo = tarfile.TarInfo(name=filename)
    tarinfo.size = len(content_bytes)
    tf.addfile(tarinfo, io.BytesIO(content_bytes))


def _build_audio_pack(tf, voice_blobs):
    for idx, voice_blob in enumerate(voice_blobs):
        with tempfile.NamedTemporaryFile(suffix='.webm') as source_f:
            # Fix for Chrome bug https://bugs.chromium.org/p/chromium/issues/detail?id=642012
            with tempfile.NamedTemporaryFile(suffix='.webm') as source_buggy_f:
                source_buggy_f.write(voice_blob)
                source_buggy_f.flush()
                _fix_chrome_webm(source_buggy_f, source_f)

            _add_to_tarfile(tf, '%d.webm' % idx, source_f.read())


@controller.route('/audio/split', 'POST')
async def audio_split(request):
    if config.IS_EDIT_BLOCKED:
        return web.HTTPForbidden()

    post_data = await request.post()

    try:
        segments = post_data['segments']
        audio_blobs_str = post_data['audio_blobs']
    except KeyError:
        return web.HTTPBadRequest()

    try:
        segments = json.loads(segments)
        if not isinstance(segments, list):
            raise ValueError()

        for segment in segments:
            if (not isinstance(segment, list)
                    or len(segment) != 2
                    or not isinstance(segment[0], int)
                    or not isinstance(segment[1], int)
                    or not segment[0] <= segment[1]):
                raise ValueError()
    except ValueError:
        return web.HTTPBadRequest(text='segments -- Invliad json format')

    audio_bin_list = []
    try:
        audio_blobs = json.loads(audio_blobs_str)
        if not isinstance(audio_blobs, list):
            raise ValueError()

        for audio_blob in audio_blobs:
            mtype, audio_data_base64 = audio_blob.split(',')
            if mtype != WEBM_BASE64_HEADER:
                return web.HTTPBadRequest(text='audio_blobs -- only support audio/webm')
            audio_bin_list.append(base64.b64decode(audio_data_base64))
    except ValueError:
        return web.HTTPBadRequest(text='audio_blobs -- Invliad json format')

    loop = asyncio.get_event_loop()
    audio_data_segments = await loop.run_in_executor(request.app['executor'],
                                                     _split_audio,
                                                     audio_bin_list,
                                                     segments)
    outputs = []
    for audio_data_segment in audio_data_segments:
        outputs.append(','.join((
            WEBM_BASE64_HEADER,
            base64.b64encode(audio_data_segment).decode('utf-8'))
        ))

    return web.json_response({
        'outputs': outputs
    })


@controller.route('/audio/download/{elicast_id:[1-9]+\d*}', 'GET')
async def audio_download(request):
    if config.IS_EDIT_BLOCKED:
        return web.HTTPForbidden()

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

        voice_blobs = json.loads(elicast.voice_blobs)

        audio_bin_list = []
        for voice_blob in voice_blobs:
            mtype, audio_data_base64 = voice_blob.split(',')
            audio_bin_list.append(base64.b64decode(audio_data_base64))

        with tempfile.NamedTemporaryFile(suffix='.tar') as output_f:
            with tarfile.open(output_f.name, 'w') as tf:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(request.app['executor'],
                                           _build_audio_pack,
                                           tf,
                                           audio_bin_list)

            return web.Response(
                body=output_f.read(),
                headers={
                    'Content-Disposition': 'attachment; filename="%s"' % ('voice_%d.tar' % elicast.id)
                }
            )


@controller.route('/audio/replace/{elicast_id:[1-9]+\d*}', 'POST')
async def audio_replace(request):
    if config.IS_EDIT_BLOCKED:
        return web.HTTPForbidden()

    elicast_id = request.match_info['elicast_id']

    post_data = await request.post()

    try:
        chunk_idx = int(post_data['chunk_idx'])
        voice_file = post_data['voice_file']
    except (ValueError, KeyError):
        return web.HTTPBadRequest()

    if not isinstance(voice_file, aiohttp.web.FileField):
        return web.HTTPNotFound(text='voice_file -- Shoule be a file')

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

        voice_blobs = json.loads(elicast.voice_blobs)

        if not (0 <= chunk_idx < len(voice_blobs)):
            return web.HTTPNotFound(text='chunk_idx -- Invalid chunk index')

        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(voice_file.filename)[1]) as source_f:
            source_f.write(voice_file.file.read())
            source_f.flush()
            with tempfile.NamedTemporaryFile(suffix='.webm') as target_f:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(request.app['executor'],
                                           _any_audio_to_webm,
                                           source_f,
                                           target_f)

                voice_blobs[chunk_idx] = WEBM_BASE64_HEADER + ',' + \
                    base64.b64encode(target_f.read()).decode('utf-8')

                elicast.voice_blobs = json.dumps(voice_blobs)
                session.add(elicast)

        return web.json_response({})
