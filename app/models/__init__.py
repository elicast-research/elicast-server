import asyncio
import datetime
from contextlib import contextmanager

from sqlalchemy import ForeignKey, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.schema import Column

__all__ = ['Session', 'SessionContext', 'Base',
           'Elicast',
           'CodeRun', 'CodeRunExercise',
           'LogTicket', 'LogEntry']

Session = scoped_session(
    sessionmaker(),
    scopefunc=asyncio.Task.current_task
)


@contextmanager
def SessionContext():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class _Base:
    query = Session.query_property()

    created = Column(types.BigInteger,
                     nullable=False,
                     default=lambda: int(datetime.datetime.now().timestamp() * 1000))


Base = declarative_base(cls=_Base)


class _CodeRunMixin:
    code = Column(types.Text, nullable=False)
    output = Column(types.Text, nullable=False)
    exit_code = Column(types.Integer, nullable=False)


class Elicast(Base):
    __tablename__ = 'elicast'

    id = Column(types.Integer, primary_key=True)

    title = Column(types.String(128), nullable=False)

    ots = Column(types.Text, nullable=False)
    voice_blobs = Column(types.Text, nullable=False)

    teacher = Column(types.String(64), nullable=True, index=True)

    is_protected = Column(types.Boolean, nullable=False, default=False)
    is_for_experiment = Column(types.Boolean, nullable=False, default=False)
    is_deleted = Column(types.Boolean, nullable=False, default=False)


class CodeRun(Base, _CodeRunMixin):
    __tablename__ = 'code_run'

    id = Column(types.Integer, primary_key=True)


class CodeRunExercise(Base, _CodeRunMixin):
    __tablename__ = 'code_run_exercise'

    id = Column(types.Integer, primary_key=True)

    elicast_id = Column(types.Integer, ForeignKey('elicast.id'),
                        nullable=False)
    elicast = relationship('Elicast')

    ex_id = Column(types.Integer, nullable=False)
    solve_ots = Column(types.Text, nullable=False)


class LogTicket(Base):
    __tablename__ = 'log_ticket'

    id = Column(types.Integer, primary_key=True)

    ticket = Column(types.String(36), nullable=False, index=True, unique=True)

    ip = Column(types.String(16), nullable=False)
    user_agent = Column(types.Text, nullable=False)
    referer = Column(types.Text, nullable=False)

    name = Column(types.String(64), nullable=False)


class LogEntry(Base):
    __tablename__ = 'log_entry'

    id = Column(types.Integer, primary_key=True)

    log_ticket_id = Column(types.Integer, ForeignKey('log_ticket.id'),
                           nullable=False)
    log_ticket = relationship('LogTicket')

    data = Column(types.Text, nullable=False)
