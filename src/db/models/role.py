from sqlalchemy import Column, Integer, String
from src.db.session import SAModel


class Role(SAModel):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    @staticmethod
    def get_all(session):
        return session.query(Role).order_by(Role.id).all()
