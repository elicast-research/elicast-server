LOGGING_LOGGER_NAME = 'elicast-server(dev)'
LOGGING_FORMAT = '[%(levelname)1.1s %(asctime)s P%(process)d %(threadName)s %(module)s:%(lineno)d] %(message)s'

DB_URI = 'sqlite:///db/dev.sqlite3'

DOCKER_URI = 'unix://var/run/docker.sock'

IS_EDIT_BLOCKED = False
