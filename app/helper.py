import functools
import logging
import os
import sys
import traceback


@functools.lru_cache()
def load_config():
    config_path = os.getenv('CONFIG_PATH', 'configs/dev.py')
    print('Config Path :', config_path)

    try:
        with open(config_path, encoding='utf-8') as f:
            config_source = f.read()
    except FileNotFoundError:
        print('Cannot find config file at "%s".' % config_path,
              file=sys.stderr)
        sys.exit(1)

    try:
        config_module_variables = dict()
        exec(config_source, config_module_variables)
    except Exception:
        traceback.print_exc()
        print('Failed to evaluate config file.', file=sys.stderr)
        sys.exit(1)

    config = type('ConfigObject', (object,), {})()
    for k, v in config_module_variables.items():
        if not k.startswith('_') and k.isupper():
            setattr(config, k, v)

    return config


config = load_config()


logger = logging.getLogger(config.LOGGING_LOGGER_NAME)


def init_logger(app_logger=None):
    if app_logger is None:
        app_logger = logging.getLogger(config.LOGGING_LOGGER_NAME)

    log_handlers = []

    # STDOUT handler
    stdout_log_handler = logging.StreamHandler(sys.stdout)
    stdout_log_handler.setFormatter(logging.Formatter(config.LOGGING_FORMAT))
    stdout_log_handler.setLevel(logging.DEBUG)
    log_handlers.append(stdout_log_handler)

    interested_loggers = [
        app_logger,
        logging.getLogger('aiohttp'),
        logging.getLogger('docker')
    ]

    for logger in interested_loggers:
        for log_hadnler in log_handlers:
            logger.addHandler(log_hadnler)

        if '--debug' in sys.argv:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    app_logger.debug('Test DEBUG log.')
    app_logger.info('Test INFO log.')

    return app_logger, log_handlers
