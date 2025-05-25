from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.db.session import SAModel


class User(SAModel):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    id_role = Column(Integer, ForeignKey("role.id"), nullable=False)
    role = relationship("Role", foreign_keys=id_role)

    @staticmethod
    def create(session, login: str, password: str, name: str, role_id: int):
        user = User(login=login, password=password, name=name, id_role=role_id)
        session.add(user)
        session.commit()
        return user

    @staticmethod
    def update_password(session, user_id: int, new_password: str):
        user = session.query(User).get(user_id)
        if user:
            user.password = new_password
            session.commit()
            return user
        return None

    @staticmethod
    def delete(session, user_id: int):
        user = session.query(User).get(user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
        return False
