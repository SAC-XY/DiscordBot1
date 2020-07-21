import logging

from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.automap import automap_base

from db.session import engine, session

logger = logging.getLogger(__name__)

Base = automap_base()
Base.prepare(engine, reflect=True)
Base.query = session.query_property()


class Message(Base):
    __tablename__ = 'メッセージ'

    @classmethod
    def 記録(cls, session, from_user_id, to_user_id, anonymous, message):
        tbl = cls.classes.メッセージ(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            anonymous=anonymous,
            message=message
        )
        session.add(tbl)
        session.flush()

        try:
            session.commit()
        except InvalidRequestError as e:
            return
