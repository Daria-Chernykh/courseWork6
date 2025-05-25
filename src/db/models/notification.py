from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.session import SAModel

class Notification(SAModel):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_equipment = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    id_state = Column(Integer, ForeignKey("state.id"), nullable=False)
    state = relationship("State", foreign_keys=id_state)
    issue_date = Column(DateTime, default=datetime.now, nullable=False)
    description = Column(String)

    @staticmethod
    def create(session, equipment_id: int, state_id: int, issue_date: datetime, description: str):
        notification = Notification(
            id_equipment=equipment_id,
            id_state=state_id,
            issue_date=issue_date,
            description=description
        )
        session.add(notification)
        session.commit()
        return notification
    
    @staticmethod
    def update(session, notification_id: int, state_id: int, description: str):
        """Обновление уведомления"""
        notification = session.query(Notification).get(notification_id)
        if notification:
            notification.id_state = state_id
            notification.description = description
            session.commit()
        return notification

    @staticmethod
    def close(session, notification_id: int):
        """Закрытие уведомления (удаление)"""
        notification = session.query(Notification).get(notification_id)
        if notification:
            session.delete(notification)
            session.commit()
            return True
        return False

    @staticmethod
    def get_all(session):
        """Получение всех уведомлений с сортировкой по дате"""
        return session.query(Notification).order_by(Notification.issue_date.desc()).all()