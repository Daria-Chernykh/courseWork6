from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from datetime import date
from src.db.session import SAModel
from src.db.models.state import State

DEFAULT_EQUIPMENT_STATE_VALUE = 'Работает'

class Equipment(SAModel, SerializerMixin):
    __tablename__ = "equipment"

    serialize_only = ('id', 'name', 'state', 'last_service_date')

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    id_state = Column(Integer, ForeignKey("state.id"), nullable=False)
    state = relationship("State", foreign_keys=id_state)
    last_service_date = Column(Date, default=date.today, nullable=False)
    notifications = relationship("Notification", backref="equipment", cascade="all, delete-orphan", passive_deletes=True)


    @staticmethod
    def create(session, name: str):
        state = session.query(State).filter(State.value == DEFAULT_EQUIPMENT_STATE_VALUE).first()
        if state is None:
            raise Exception(f'No State with name equal to {DEFAULT_EQUIPMENT_STATE_VALUE=}')
        return Equipment(name=name, id_state=state.id)

    @staticmethod
    def update(session, equipment_id: int, name: str, service_date: date):
        equipment = session.query(Equipment).get(equipment_id)
        if equipment:
            equipment.name = name
            equipment.last_service_date = service_date
            session.commit()
        return equipment

    @staticmethod
    def delete(session, equipment_id):
        equipment = session.query(Equipment).get(equipment_id)
        if not equipment:
            return False
        
        for notification in equipment.notifications:
            session.delete(notification)
        
        session.delete(equipment)
        session.commit()
        return True

    @staticmethod
    def report_fault(session, equipment_id: int, service_date: date):
        """Обновляет состояние оборудования на 'Требуется техническое обслуживание' 
        и устанавливает дату последнего обслуживания"""
        fault_state = session.query(State).filter(
            State.value == "Требуется техническое обслуживание"
        ).first()
        
        if not fault_state:
            raise ValueError("State 'Требуется техническое обслуживание' not found")
        
        equipment = session.query(Equipment).get(equipment_id)
        if equipment:
            equipment.id_state = fault_state.id
            equipment.last_service_date = service_date
            session.commit()
        return equipment
    
    @staticmethod
    def change_state(session, equipment_id: int, state_id: int):
        """Изменение состояния оборудования"""
        equipment = session.query(Equipment).get(equipment_id)
        if equipment:
            equipment.id_state = state_id
            session.commit()
        return equipment

    @staticmethod
    def set_working_state(session, equipment_id: int):
        """Установка состояния 'Работает' для оборудования"""
        working_state = session.query(State).filter(State.value == "Работает").first()
        if not working_state:
            raise ValueError("State 'Работает' not found")
            
        equipment = session.query(Equipment).get(equipment_id)
        if equipment:
            equipment.id_state = working_state.id
            session.commit()
        return equipment