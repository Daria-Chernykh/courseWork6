from sqlalchemy import Column, Integer, String
from sqlalchemy_serializer import SerializerMixin
from src.db.session import SAModel


class State(SAModel, SerializerMixin):
    __tablename__ = "state"

    serialize_only = ('id', 'value')

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String, unique=True, nullable=False)

    @staticmethod
    def get_by_value(session, value: str):
        return session.query(State).filter(State.value == value).first()

    @staticmethod
    def get_all(session):
        return session.query(State).order_by(State.id).all()

    @staticmethod
    def get_maintenance_states(session):
        """Получение состояний для технического обслуживания"""
        return session.query(State).filter(
            State.value.in_(["Требуется техническое обслуживание", "В ремонте"])
        ).all()

    @staticmethod
    def get_working_state(session):
        """Получение состояния 'Работает'"""
        return session.query(State).filter(State.value == "Работает").first()