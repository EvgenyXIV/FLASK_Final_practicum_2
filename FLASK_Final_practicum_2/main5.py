from flask import Flask, render_template,request, redirect, url_for, current_app, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user,logout_user
import os
import json
from datetime import date, datetime, timedelta, UTC

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['LOGIN_DISABLED'] = True
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)

class Card(db.Model):                      # Создание модели таблицы Notes в базе данных diary.db
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    subtitle = db.Column(db.String(100))
    text = db.Column(db.Text)

# Наследование класса UserMixin добавляет в класс User методы
# is_authenticated(), is_active(), is_anonymous(), get_id(), использующиеся для проверки пользователей.
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)


"""
Загружаем модель в приложение app через терминал:
    команды  \6_FLASK\\FLASK_Final_practicum_2>
    >python                             # Запустили пайтон
    >from main5 import app, db          # Указали пайтону переменные для работы с нашей базой - 
                                        # приложение app и объект с экземпляром базы db 
    >app.app_context().push()           # Отправили в базу её содержимое (таблицу)
    >db.create_all()                    # Создали нашу базу notes.db
    >quit()                             # Выходим из пайтона
"""
"""
 Настраиваем работу Flask-Migrate через терминал:
    команды  \6_FLASK\\FLASK_Final_practicum_2>
    >set FLASK_APP=main5.py          # указываем  рабочий файл main5.py
    >$env:FLASK_APP="main5.py"       # если команда set не сработает и сообщение No such command 'db'
                                      # (так бывает, если имя файла не app.py)
                                      
    >flask db init                    # создание поддиректории migrations в конфигурации, если её нет, 
                                      # для регистрации изменений схемы базы db
                                      
    >flask db migrate                 # База изменила схему - создаём миграцию базы  
    
    >flask db upgrade                 # После миграции базы выполняем апгрейд базы данных                                 
"""


expiration = datetime.now(UTC)  # Глобальная переменная, используется установки времени авторизации
count = 0                       # Глобальные переменные, используются при внесении изменений
change_id = None                   # в таблицы базы данных notes.db


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(Users).get(user_id)

# Маршрут "/register" регистрации нового пользователя по шаблону "register.html".
# При любой ошибке ввода-получения данных происходит возврат на страницу регистрации.
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            username, email, password = (
                                        request.form["username_m"],
                                        request.form["email_m"],
                                        request.form["password_m"]
                                        )
            # пока не реализован метод формирования токена:
            token = username + email + password
            user = Users(username=username, email=email, password=password, token=token)
            db.session.add(user)
            db.session.commit()
            flash("Пользователь зарегистрирован")
            return redirect(url_for("home"))
        except:
            return render_template("register.html")
    else:
        flash("Зарегистрируйтесь для входа")
        return render_template("register.html")

# Маршрут "/login" авторизации пользователя по шаблону "login.html"
@app.route("/login/", methods=["GET", "POST"])
def login():
    global expiration
    if request.method == "GET":
        return render_template("login.html")
    else:
        user = Users.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            token = user.token
            expiration = datetime.now(UTC) + timedelta(minutes=30)  # Задано время жизни регистрации (30 минут)
            session["token"] = token                                # Создана сессия "token" со значением token,
                                                                    #  сессия - объект как словарь{ключ:значение}
            flash(f"Пользователь {user.username} успешно зарегистрирован")
            return redirect("http://127.0.0.1:5000//home")  # Переход на гл.страницу, если авторизация удачна.
        elif user and user.password != request.form["password"]:
            flash("Ошибка в пароле")
            return render_template("login.html")
        else:
            flash("Пользователь не зарегистрирован")
            return redirect(url_for("home"))

# Маршрут "/logout" выхода пользователя из системы пользователя по кнопке "Выйти" на странице "/login"
@app.route('/logout/', methods=["POST", "GET"])
@login_required
def logout():
    session.pop("token", None)  # Удаление токена "token" из списка session
    logout_user()
    flash("user logged out")
    return redirect(url_for("home"))

# Маршрут "/home" для перехода на маршруты регистрации, авторизации, главной страницы.
@app.route('/home', methods=["POST", "GET"])
def home():
    return render_template("home.html")
  
@app.route('/', methods=["POST", "GET"])
def index():
    # Установка рабочей директории, в которой находится главный py-код (main5.py)
    os.chdir(r"C:\\Users\\EvgenyMINI_S\\PythonProjects\\PythonProject\\6_FLASK\\FLASK_Final_practicum_2")

    global count, change_id  # переменные используются при внесении изменений в таблицы базы данных diary.db


    # ВХОД В СИСТЕМУ

    # Проверка актуальности авторизации пользователя.
    # Любая операция на сервере доступна только авторизованным пользователям.
    if not session.get("token") or datetime.now(UTC) >= expiration:  # Если токен есть и время его жизни
        # больше текущего времени, то сессия продолжается
        flash("Время сессии истекло или ошибка в логине/пароле. Повторите вход.")  # flash-message будет отражено на стр. "/home"
        return redirect(url_for("home"))
    else:
        pass

        # Б А З А   Д А Н Н Ы Х    diary.db
        # Проверяем есть ли запросы на передачу изменений в базу данных
        # и, если есть, получаем их и загружаем в базу.
        # Появление любой ошибки при загрузке игнорируется.

        # Т А Б Л И Ц А   C A R D
        # ДОБАВЛЕНИЕ новой записи в таблицу Card - ЗАПРОС НА
        try:  # Получение данных из форм "title", "subtitle", "text" (index.html)
            title, subtitle, text = (request.form["title"], request.form["subtitle"], request.form["text"])
            # Создание объекта-таблицы с указанными полями колонок
            record = Card(
                            title=title,
                            subtitle=subtitle,
                            text=text
                        )
            # Инициализация объекта с базой данных db и загрузка записи в таблицу Card
            db.session.add(record)  # Инициализация объекта с базой данных db и
            # Сохранение изменений в базе данных
            db.session.commit()
        except Exception:
            pass

        # ИЗМЕНЕНИЕ записи из таблицы Card по id
        try:
            # Если счётчик 0, то счётчик меняется на 1, выводится запись для контроля изменений,
            # поле id для подтверждения, поля ввода новых значений, кнопка submit
            # Если счётчик 1, а кнопка submit не была нажата при предыдущей сессии изменений,
            # то возникает исключение, которое обрабатывается и счётчик меняется на 0
            # и сервер готов для новых изменений.
            if count == 0:
                change_id = int(request.form["change_id"])
                record = db.session.query(Card).filter(Card.id == change_id).first() # форма "change_id" (index.html)
                count += 1
                return render_template("index.html",
                                       change_id=change_id,
                                       record=record
                                       )
            # Получение данных из форм "change_id_n", "title_n "subtitle_n", "text_n" (index.html)
            change_id_n, title, subtitle, text = (int(request.form["change_id_n"]),
                                                request.form["title_n"],
                                                request.form["subtitle_n"],
                                                request.form["text_n"]
                                                )
            if change_id_n != change_id:    # Проверка id для подтверждения изменений
                flash("id для внесения изменений не подтверждён")
                return redirect("home")
            # Создание объекта-запись record1 и установка новых значений в поля объекта
            record1 = db.session.query(Card).filter(Card.id == change_id).first()
            if len(title) == 0: title = record1.title
            else: pass
            if len(subtitle) == 0: subtitle = record1.subtitle
            else: pass
            if len(text) == 0: text = record1.text
            else: pass
            record1.title = title
            record1.subtitle = subtitle
            record1.text = text
            count = 0
            change_id = None
            db.session.commit()  # Сохранение изменений в базе данных
        except Exception:
            count = 0

        # УДАЛЕНИЕ записи из таблицы Card по id
        try:
            del_id = int(request.form["del_id"])  # Запрос из формы "del_id" (index.html)
            record = db.session.query(Card).filter(Card.id == del_id).first()  # Создание объекта-записи с id=del_id
            db.session.delete(record)  # Удаление записи record из объекта db
            db.session.commit()  # Сохранение изменений в базе данных
        except Exception:
            pass

        # ВЫВОД таблицы Card по условию print_card="Y"
        try:
            print_card = None
            print_card = request.form["print_card"]
            cards = Card.query.all()
            return render_template("index.html", print_card=print_card, cards=cards)
        except Exception:
            return render_template("index.html")


"""     ЭТОТ БЛОК С ТАБЛИЦЕЙ U S E R S НЕ ИСПОЛЬЗУЕТСЯ, ВРЕМЕННО ИСКЛЮЧЁН...
        # Т А Б Л И Ц А   U S E R S
        # ДОБАВЛЕНИЕ новой записи в таблицу Users
        try:  # Запрос из форм "username", "email", "password" (index.html)
            username1, email1, password1 = (request.form["username"], request.form["email"], request.form["password"])
            # пока не реализован метод формирования токена:
            token1 = username1 + email1 + password1
            record1 = Users(username=username1, email=email1, password=password1,
                            token=token1)  # Создание объекта-таблицы с указанными полями колонок
            db.session.add(record1)  # Инициализация объекта с базой данных db и
            # загрузка записи в таблицу Users
            db.session.commit()  # Сохранение изменений в базе данных
        except Exception:
            pass

        # ИЗМЕНЕНИЕ записи из таблицы Users по id
        try:
            # Если счётчик 0, то счётчик меняется на 1, выводится запись для контроля изменений,
            # поле id для подтверждения, поля ввода новых значений, кнопка submit
            # Если счётчик 1, а кнопка submit пр предыдущей сессии изменений не была нажата,
            # то возникает исключение, которое обрабатывается, счётчик меняется на 0
            # и сервер готов для новых изменений.
            if count == 0:
                change_user_id2 = int(request.form["change_user_id"])
                record2 = db.session.query(Users).filter(
                    Users.id == int(change_user_id2)).first()  # форма "change_user_id" (index15.html)
                count += 1
                print('count2=', count)
                return render_template("index.html",
                                       change_user_id=change_user_id2,
                                       record=record2
                                       )
        except Exception:
            pass
        try:
            change_user_id_k, username_k, email_k, password_k = (int(request.form["change_user_id_k"]),
                                                                 request.form["username_k"],
                                                                 request.form["email_k"],
                                                                 request.form["password_k"]
                                                                 )
            # пока не реализован метод формирования токена:
            token3 = username_k + email_k + password_k

            record3 = db.session.query(Users).filter(Users.id == change_user_id_k).first()
            record3.username = username_k
            record3.email = email_k
            record3.password = password_k
            record3.token = token3
            count = 0
            db.session.commit()  # Сохранение изменений в базе данных
        except Exception:
            count = 0

        # УДАЛЕНИЕ записи из таблицы Users по id
        try:
            del_user_id = int(request.form["del_user_id"])  # Запрос из формы "del_user_id" (index15.html)
            user = db.session.query(Users).filter(
                Users.id == del_user_id).first()  # Создание объекта-записи с id=del_user_id
            db.session.delete(user)  # Удаление записи record из объекта db
            db.session.commit()  # Сохранение изменений в базе данных
            return render_template("index.html")
        except Exception:
            return render_template("index.html")

"""

@app.route("/card", methods=["POST", "GET"])
@login_required
def card():
    # Проверка актуальности авторизации пользователя.
    # Любая операция на сервере доступна только авторизованным пользователям.
    if not session.get("token") or datetime.now(UTC) >= expiration:  # Если токен есть и время его жизни
                                                                     # больше текущего времени, то сессия продолжается
        flash("время сессии истекло или ошибка в логине/пароле")
        return redirect("home")
    else:
        return render_template("card.html")


@app.route('/create', methods=["POST", "GET"])
#@login_required
def create():
    """ if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    else:
        return redirect(url_for("form_create"))"""

    # Проверка актуальности авторизации пользователя.
    # Любая операция на сервере доступна только авторизованным пользоватеям.
    if not session.get("token") or datetime.now(UTC) <= expiration: # Если токен есть и время его жизни
                                                                    # больше текущего времени, то сессия продолжается
        return redirect("form_create")
    else:
        flash("Время сессии истекло или ошибка в логине/пароле. Повторите вход.")
        return redirect("home")



@app.route('/form_create', methods=['GET','POST'])
@login_required
def form_create():
    try:
        title, subtitle, text = (request.form["title"], request.form["subtitle"], request.form["text"])
        if len(title) == 0 or len(subtitle) == 0 or len(text) == 0:
            flash("поля сообщения не могут быть пустыми")
            return redirect("home")
        else:
            record = Card(title=title, subtitle=subtitle, text=text)  # Инициализация объекта row таблицы Card
            db.session.add(record)                                    # и загрузка записи в таблицу Card.
            db.session.commit()                                       # Сохранение изменений в базе данных.
            return redirect("home")
    except Exception:
        return render_template('form_create.html')

if __name__ == "__main__":
    app.secret_key = 'lol'
    app.run(debug=True)
