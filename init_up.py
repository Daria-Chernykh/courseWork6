from os import getenv
from dotenv import load_dotenv
from src.db.session import init, create_session
from src.db.models.role import Role
from src.db.models.state import State
from src.db.models.status import Status

load_dotenv()
init(getenv("DB_URL"))

with create_session() as session:
    for s in "В обработке", "Подготовка материалов", "Сортировка", "Упаковка", "Подготовка к отгрузке", "Проверка качества", "Закрыт":
        session.add(Status(value=s))
    
    for s in "Работает", "Требуется техническое обслуживание", "В ремонте":
        session.add(State(value=s))

    for s in "Администратор системы", "Оператор упаковочных линий", "Инженер по техническому обслуживанию":
        session.add(Role(name=s))

    session.commit()