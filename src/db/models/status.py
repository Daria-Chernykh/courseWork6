from sqlalchemy import Column, Integer, String
from src.db.session import SAModel


class Status(SAModel):
    __tablename__ = "status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String, unique=True, nullable=False)

    @staticmethod
    def get_all(session):
        return session.query(Status).order_by(Status.id).all()
