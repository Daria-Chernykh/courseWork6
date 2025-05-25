from flask import Flask, render_template, request, redirect, url_for, flash
from flask import session as flask_session
from os import getenv
from dotenv import load_dotenv
from datetime import datetime, date
from sqlalchemy import null
from src.db.session import init, create_session

from src.db.models.user import User
from src.db.models.role import Role
from src.db.models.equipment import Equipment
from src.db.models.notification import Notification
from src.db.models.order import Order
from src.db.models.product import Product
from src.db.models.state import State
from src.db.models.status import Status
from src.db.models.product_to_order_association import ProductToOrderAssociation 

from werkzeug.security import check_password_hash
from functools import wraps
import json

app = Flask(__name__)
app.json.ensure_ascii = False
app.secret_key = "supersecretkey" 

@app.route("/")
def index():
    return "Hello, world!"

@app.route("/login", methods=["GET", "POST"])
def login():
    with create_session() as db:
        if request.method == "POST":
            login = request.form["login"]
            password = request.form["password"]
            user = db.query(User).filter_by(login=login).first()
            if user and check_password_hash(user.password, password):
                flask_session["user_id"] = user.id
                flask_session["user_name"] = user.name
                flask_session["user_role"] = user.role.name
                flask_session["user_role_id"] = user.id_role  # если используешь id роли
                return redirect(url_for("home"))
            return render_template("login.html", error="Неверный логин или пароль")
        return render_template("login.html")

@app.route("/logout")
def logout():
    flask_session.clear()
    return redirect(url_for("login"))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in flask_session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/home")
@login_required
def home():
    if "user_id" not in flask_session:
        return redirect(url_for("login"))

    role = flask_session.get("user_role")
    name = flask_session.get("user_name")
    
    role_buttons = {
        "Администратор системы": ["Оборудование", "Пользователи", "Текущие заказы", "Архив заказов"],
        "Оператор упаковочных линий": ["Оборудование", "Текущие заказы"],
        "Инженер по техническому обслуживанию": ["Оборудование", "Уведомления"],
    }

    buttons = role_buttons.get(role, [])

    return render_template("home.html", name=name, role=role, buttons=buttons)

@app.route("/equipments", methods=["GET", "POST"])
@login_required
def show_equipments():
    with create_session() as session:
        if request.method == "GET":
            equipments = session.query(Equipment).order_by(Equipment.id).all()
            return render_template("equipments.html", equipments=equipments)
        
        if request.method == "POST":
            # Обработка добавления оборудования
            if 'equipment-name' in request.form:
                name = request.form.get('equipment-name').strip()
                if not name:
                    return 'Empty equipment name', 400
                if session.query(Equipment).filter(Equipment.name == name).first() is not None:
                    return 'Equipment with this name already exists', 400
                equipment = Equipment.create(session, name)
                session.add(equipment)
                session.commit()
                return redirect(url_for('show_equipments'))
            
            # Обработка редактирования оборудования
            elif 'edit-equipment-name' in request.form:
                equipment_id = request.form.get('edit-equipment-id')
                name = request.form.get('edit-equipment-name').strip()
                service_date = request.form.get('edit-equipment-date')
                
                if not name:
                    return 'Empty equipment name', 400
                
                try:
                    date_obj = datetime.strptime(service_date, "%Y-%m-%d").date() if service_date else None
                    if date_obj and date_obj > date.today():
                        return "Service date cannot be in the future", 400
                        
                    Equipment.update(session, equipment_id, name, date_obj)
                    return redirect(url_for('show_equipments'))
                except ValueError:
                    return "Invalid date format", 400
            
            # Обработка уведомления о неисправности
            elif 'fault-detection-date' in request.form:
                equipment_id = request.form.get('fault-equipment-id')
                detection_date = request.form.get('fault-detection-date')
                description = request.form.get('fault-description').strip()
                
                if not description:
                    return 'Description is required', 400
                
                try:
                    # Парсим дату и проверяем корректность
                    date_obj = datetime.strptime(detection_date, "%Y-%m-%d").date()
                    if date_obj > date.today():
                        return "Detection date cannot be in the future", 400
                    
                    # Обновляем оборудование (состояние и дату обслуживания)
                    equipment = Equipment.report_fault(
                        session=session,
                        equipment_id=equipment_id,
                        service_date=date_obj
                    )
                    
                    if not equipment:
                        return "Equipment not found", 404
                    
                    # Получаем состояние "Требуется техническое обслуживание"
                    fault_state = session.query(State).filter(
                        State.value == "Требуется техническое обслуживание"
                    ).first()
                    
                    if not fault_state:
                        return "Required equipment state not found", 500
                    
                    # Создаем уведомление
                    Notification.create(
                        session=session,
                        equipment_id=equipment_id,
                        state_id=fault_state.id,
                        issue_date=datetime.now(),  # Текущая дата и время
                        description=description
                    )
                    
                    return redirect(url_for('show_equipments'))
                    
                except ValueError as e:
                    return str(e), 400

@app.route("/equipment/delete", methods=["POST"])
@login_required
def delete_equipment():
    with create_session() as db:
        equipment_id = request.form.get('id')
        equipment = db.query(Equipment).get(equipment_id)

        if not equipment:
            flash("Оборудование не найдено", "danger")
            return redirect(url_for("show_equipments"))

        # Удаление оборудования и связанных уведомлений
        for notification in equipment.notifications:
            db.delete(notification)
        db.delete(equipment)
        db.commit()

        flash("Оборудование и связанные уведомления удалены", "success")
        return redirect(url_for("show_equipments"))

@app.route("/users", methods=["GET", "POST"])
@login_required
def show_users():
    if flask_session.get("user_role") not in ["Администратор системы"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        if request.method == "GET":
            users = session.query(User).order_by(User.id).all()
            roles = session.query(Role).all()
            return render_template("users.html", users=users, roles=roles)
        
        if request.method == "POST":
            # Обработка добавления пользователя
            if 'login' in request.form and 'name' in request.form:
                login = request.form.get('login').strip()
                password = request.form.get('password').strip()
                name = request.form.get('name').strip()
                role_id = request.form.get('role_id')
                
                if not all([login, password, name, role_id]):
                    return 'All fields are required', 400
                
                if session.query(User).filter(User.login == login).first() is not None:
                    return 'User with this login already exists', 400
                
                # Хеширование пароля (реализуйте свою функцию хеширования)
                hashed_password = hash_password(password)
                
                user = User(
                    login=login,
                    password=hashed_password,
                    name=name,
                    id_role=role_id
                )
                session.add(user)
                session.commit()
                return redirect(url_for('show_users'))
            
            # Обработка смены пароля
            elif 'new_password' in request.form:
                user_id = request.form.get('user_id')
                new_password = request.form.get('new_password').strip()
                
                if not new_password:
                    return 'Password is required', 400
                
                user = session.query(User).get(user_id)
                if user:
                    user.password = hash_password(new_password)
                    session.commit()
                    return redirect(url_for('show_users'))
                return 'User not found', 404

@app.route("/user/delete", methods=["POST"])
@login_required
def delete_user():
    if flask_session.get("user_role") not in ["Администратор системы"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        user_id = request.form.get('id')
        user = session.query(User).get(user_id)
        if user:
            session.delete(user)
            session.commit()
            return redirect(url_for('show_users'))
        return 'User not found', 404

# Функция хеширования пароля (замените на свою реализацию)
def hash_password(password):
    # Пример: используйте bcrypt или другой безопасный метод
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

@app.route("/notifications", methods=["GET"])
@login_required
def show_notifications():
    if flask_session.get("user_role") not in ["Инженер по техническому обслуживанию"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        notifications = Notification.get_all(session)
        states = State.get_maintenance_states(session)
        return render_template("notifications.html", 
                            notifications=notifications, 
                            states=states)

@app.route("/notification/update", methods=["POST"])
@login_required
def update_notification():
    if flask_session.get("user_role") not in ["Инженер по техническому обслуживанию"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        notification_id = request.form.get('notification_id')
        equipment_id = request.form.get('equipment_id')
        state_id = request.form.get('state_id')
        description = request.form.get('description')
        
        # Обновляем уведомление
        notification = Notification.update(
            session=session,
            notification_id=notification_id,
            state_id=state_id,
            description=description
        )
        
        # Обновляем состояние оборудования
        Equipment.change_state(
            session=session,
            equipment_id=equipment_id,
            state_id=state_id
        )
        
        return redirect(url_for('show_notifications'))

@app.route("/notification/close", methods=["POST"])
@login_required
def close_notification():
    if flask_session.get("user_role") not in ["Инженер по техническому обслуживанию"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        notification_id = request.form.get('notification_id')
        equipment_id = request.form.get('equipment_id')
        
        # Переводим оборудование в состояние "Работает"
        Equipment.set_working_state(
            session=session,
            equipment_id=equipment_id
        )
        
        # Закрываем уведомление
        Notification.close(
            session=session,
            notification_id=notification_id
        )
        
        return redirect(url_for('show_notifications'))

@app.route("/orders", methods=["GET", "POST"])
@login_required
def show_orders():
    if flask_session.get("user_role") not in ["Администратор системы", "Оператор упаковочных линий"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        if request.method == "POST":
            customer = request.form.get("customer")
            delivery_info = request.form.get("delivery_info")
            product_data = request.form.get("product_data")
            if not customer or not product_data:
                flash("Заполните все обязательные поля", "danger")
                return redirect(url_for("show_orders"))
            try:
                product_list = json.loads(product_data)  # [{"id": "1", "qty": 3}, ...]
            except json.JSONDecodeError:
                flash("Ошибка в данных о товарах", "danger")
                return redirect(url_for("show_orders"))
            # Получаем статус "В обработке"
            status = session.query(Status).filter_by(value="В обработке").first()
            if not status:
                status = Status(value="В обработке")
                session.add(status)
                session.flush()
            new_order = Order(
                customer=customer,
                delivery_info=delivery_info,
                open_date=datetime.now(),
                status=status,
                operator=None
            )
            session.add(new_order)
            session.flush()
            # Добавляем продукты с учетом количества
            for item in product_list:
                product_id = int(item["id"])
                quantity = int(item["qty"])
                product = session.get(Product, product_id)
                if not product:
                    continue
                # Добавляем связь с количеством
                assoc = ProductToOrderAssociation(
                    id_order=new_order.id,
                    id_product=product_id,
                    count=quantity
                )
                session.add(assoc)
            session.commit()
            flash("Заказ успешно создан", "success")
            return redirect(url_for("show_orders"))

        # GET: отображение
        if flask_session.get("user_role") == "Оператор упаковочных линий":
            orders = session.query(Order).filter(
                Order.id_operator == flask_session.get("user_id"),
                Order.close_date == None
            ).all()
        else:
            orders = session.query(Order).filter(
                Order.close_date == None
            ).all()

        products = session.query(Product).order_by(Product.name).all()
        users = session.query(User).join(Role).filter(Role.name == "Оператор упаковочных линий").all()

        statuses = session.query(Status).all()
        return render_template(
            "orders.html",
            orders=orders,
            products=products,
            users=users,
            statuses=statuses,
            user_role=flask_session.get("user_role")
        )


@app.route("/order/update", methods=["POST"])
@login_required
def update_order():
    if flask_session.get("user_role") not in ["Администратор системы", "Оператор упаковочных линий"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        order_id = request.form.get("order_id")

        order = session.query(Order).get(order_id)
        if not order:
            flash("Заказ не найден", "danger")
            return redirect(url_for("show_orders"))

        # Администратор может редактировать эти поля
        if flask_session.get("user_role") == "Администратор системы":
            customer = request.form.get("customer")
            delivery_info = request.form.get("delivery_info")
            operator_id = request.form.get("id_operator")

            if customer:
                order.customer = customer
            if delivery_info:
                order.delivery_info = delivery_info
            if operator_id:
                order.id_operator = operator_id or None

        # Оператор может редактировать эти поля
        elif flask_session.get("user_role") == "Оператор упаковочных линий":
            note = request.form.get("note")
            status_id = request.form.get("id_status")

            if note is not None:
                order.note = note
            if status_id:
                order.id_status = status_id
                # Получаем статус по ID
                selected_status = session.query(Status).get(status_id)
                if selected_status and selected_status.value == "Закрыт":
                    order.close_date = datetime.today()
                else:
                    order.close_date = None  # можно оставить как есть

        session.commit()
        flash("Заказ успешно обновлён", "success")
        return redirect(url_for("show_orders"))

@app.route("/order/close", methods=["POST"])
@login_required
def close_order():
    if flask_session.get("user_role") not in ["Оператор упаковочных линий", "Администратор системы"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))

    order_id = request.form.get("order_id")
    with create_session() as session:
        order = session.query(Order).get(order_id)
        if not order:
            return 'Order not found', 404

        order.close_date = datetime.today()
        session.commit()
    return 'Success', 200

@app.route("/archive", methods=["GET"])
@login_required
def show_archive():
    if flask_session.get("user_role") not in ["Администратор системы"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    with create_session() as session:
        # Только закрытые заказы (у которых close_date не null)
        orders = session.query(Order).filter(Order.close_date.isnot(None)).order_by(Order.close_date.desc()).all()
        return render_template("archive.html", orders=orders)

@app.route("/order/delete", methods=["POST"])
@login_required
def delete_order():
    if flask_session.get("user_role") not in ["Администратор системы", "Оператор упаковочных линий"]:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("home"))
    
    order_id = request.form.get("order_id")
    if not order_id:
        flash("ID заказа не указан", "danger")
        return redirect(url_for("show_archive"))

    with create_session() as session:
        order = session.query(Order).get(order_id)
        if not order:
            flash("Заказ не найден", "danger")
            return redirect(url_for("show_archive"))

        session.query(ProductToOrderAssociation).filter_by(id_order=order_id).delete()
        session.delete(order)
        session.commit()
        flash("Заказ успешно удалён", "success")
        return redirect(url_for("show_archive"))


if __name__ == "__main__":
    load_dotenv()
    init(getenv("DB_URL"))
    app.run()