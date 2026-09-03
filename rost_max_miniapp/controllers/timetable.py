# -*- coding: utf-8 -*-
import secrets
import re
import base64
from datetime import timedelta
from odoo import http
from odoo.http import request
from odoo import fields, tools
import logging
from odoo.exceptions import AccessDenied
from .session_middleware import restore_session_if_needed

_logger = logging.getLogger(__name__)

# Ключ сессии для нашего стабильного CSRF-токена (без o<timestamp>, в отличие
# от session['csrf_token'] Odoo). Токен создаётся лениво и не меняется в рамках
# сессии -> детерминированное сравнение на POST (без хрупкости time-suffixed
# формата Odoo, который ломался при разнице времени рендера и отправки).
CSRF_SESSION_KEY = 'spa_csrf_token'

# Trusted device cookie name (совпадает с auth_totp)
TRUSTED_DEVICE_COOKIE = 'td_id'
TRUSTED_DEVICE_AGE = 90 * 86400  # 90 days

# Веб-версии MAX (web.max.ru) и Telegram (web.telegram.org) открывают миниапп
# в iframe. Odoo по умолчанию не пускает чужие домены. X-Frame-Options не
# используем вовсе: ALLOW-FROM удалён из стандартов и игнорируется
# браузерами, а SAMEORIGIN запрещал бы встраивание — всю работу делает
# CSP frame-ancestors (приоритетнее XFO в современных браузерах).
MAX_FRAME_HEADERS = {
    'Content-Security-Policy': (
        'frame-ancestors https://*.max.ru https://web.telegram.org '
        'https://telegram.org https://*.telegram.org'
    ),
}


def _spa_response(template, **ctx):
    """Рендер SPA-страницы с заголовками, разрешающими iframe из MAX."""
    response = request.render(template, ctx)
    response.headers.update(MAX_FRAME_HEADERS)
    return response


def _get_spa_csrf_token():
    """Стабильный CSRF-токен SPA, хранящийся в сессии под нашим ключом."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)  # 256-bit случайный secret
        request.session[CSRF_SESSION_KEY] = token
    return token


def _check_spa_csrf():
    """Ручная валидация CSRF для JSON POST (системный валидатор Odoo для
    http-роутов ищет токен только в query/form-data, а фронт шлёт его в
    заголовке X-CSRF-Token). Сравниваем с нашим стабильным токеном SPA.

    Возвращает Response (400) при несовпадении, иначе None.
    """
    csrf_token = request.httprequest.headers.get('X-CSRF-Token')
    session_token = request.session.get(CSRF_SESSION_KEY)
    if not session_token or not csrf_token or csrf_token != session_token:
        return request.make_json_response({"error": "CSRF validation failed"}, status=400)
    return None


def _check_trusted_device(user):
    """Проверяет, является ли текущее устройство доверенным для пользователя с 2FA."""
    if not user.totp_enabled:
        return True
    key = request.cookies.get(TRUSTED_DEVICE_COOKIE)
    if not key:
        return False
    return request.env['auth_totp.device']._check_credentials_for_uid(
        scope="browser", key=key, uid=user.id
    )


def _generate_trusted_device_cookie(response, user):
    """Генерирует и устанавливает cookie доверенного устройства."""
    from datetime import datetime, timedelta
    name = f"{request.httprequest.user_agent.browser.capitalize()} on {request.httprequest.user_agent.platform.capitalize()}"
    if request.geoip.city.name:
        name += f" ({request.geoip.city.name}, {request.geoip.country_name})"

    key = request.env['auth_totp.device'].sudo()._generate(
        "browser",
        name,
        datetime.now() + timedelta(seconds=TRUSTED_DEVICE_AGE)
    )
    response.set_cookie(
        key=TRUSTED_DEVICE_COOKIE,
        value=key,
        max_age=TRUSTED_DEVICE_AGE,
        httponly=True,
        samesite='Lax'
    )
    return key


def _get_user_students(user):
    """Определить роль пользователя и список "его" учеников (op.student).

    Возвращает (role, students):
      role: 'admin' | 'teacher' | 'student' | 'parent' | 'guest'
      students: recordset op.student, чьи данные видит юзер:
        - teacher/admin -> пустой recordset (видят всё, ограничений по ученикам нет)
        - student       -> сам ученик
        - parent        -> дети (op.parent.student_ids)
    """
    if user.has_group('base.group_system'):
        return 'admin', request.env['op.student'].browse()
    faculty = request.env['op.faculty'].sudo().search([
        ('partner_id', '=', user.partner_id.id)
    ], limit=1)
    if faculty:
        return 'teacher', request.env['op.student'].browse()
    student = request.env['op.student'].sudo().search([
        ('partner_id', '=', user.partner_id.id)
    ], limit=1)
    if student:
        return 'student', student
    parent = request.env['op.parent'].sudo().search([
        ('name', '=', user.partner_id.id)
    ], limit=1)
    if parent:
        return 'parent', parent.student_ids
    return 'guest', request.env['op.student'].browse()


def _check_lesson_write_access(sheet):
    """Защита от фальсификации оценок: писать может только админ либо
    преподаватель, назначенный вести этот урок. Гость/студент/чужой
    преподаватель получают 403.

    Возвращает Response (403) при отказе, иначе None.
    """
    user = request.env.user
    is_admin = user.has_group('base.group_system')
    if is_admin:
        return None
    faculty = request.env['op.faculty'].sudo().search([
        ('partner_id', '=', user.partner_id.id)
    ], limit=1)
    if not faculty or sheet.faculty_id != faculty:
        _logger.warning(
            "Security write violation: User %s (ID %s) attempted to write grades on unauthorized lesson ID %s",
            user.login, user.id, sheet.id,
        )
        return request.make_json_response(
            {"error": "У вас нет прав для изменения оценок этого урока"}, status=403
        )
    return None


class RostMaxTimetableController(http.Controller):
    """Мини-приложение для MAX: расписание занятий"""

    @http.route("/rost_max/login", type="http", auth="public", methods=["GET", "POST"], cors="*", csrf=False)
    def login_page(self, **kw):
        """API: аутентификация. GET возвращает SPA, POST - login"""
        if request.httprequest.method == 'POST':
            try:
                body = request.get_json_data()
            except Exception:
                return request.make_json_response(
                    {"error": "Invalid JSON"}, status=400
                )

            login = body.get('login')
            password = body.get('password')
            remember_me = body.get('remember_me', False)
            # csrf_token валидируется через заголовок X-CSRF-Token в _check_spa_csrf для API роутов
            # здесь для /rost_max/login используем свою проверку если нужно

            if not login or not password:
                return request.make_json_response(
                    {"error": "Email и пароль обязательны"}, status=400
                )

            try:
                credential = {'login': login, 'password': password, 'type': 'password'}
                auth_info = request.session.authenticate(request.db, credential)
                if not auth_info.get('uid'):
                    return request.make_json_response(
                        {"error": "Неверные учетные данные"}, status=400
                    )

                # authenticate() -> finalize() ставит should_rotate=True: Odoo
                # в конце запроса сгенерирует НОВЫЙ sid, и sid, отданный ниже
                # cookie, отданной ниже в JSON/Set-Cookie, умрёт. Гасим
                # ротацию, чтобы session_id в ответе и в X-Session-Id
                # fallback оставался валидным.
                request.session.should_rotate = False

                request.session['is_timetable_user'] = True
                user = request.env['res.users'].browse(auth_info['uid'])
                is_admin = user.has_group('base.group_system')

                # Проверяем 2FA
                if user.totp_enabled:
                    # Проверяем доверенное устройство
                    if _check_trusted_device(user):
                        # Устройство доверено - пропускаем 2FA
                        pass
                    else:
                        # Нужно 2FA - сохраняем pre_uid и возвращаем challenge
                        request.session.pre_uid = auth_info['uid']
                        return request.make_json_response({
                            "success": False,
                            "require_2fa": True,
                            "two_factor_enabled": True,
                            "user_name": user.name,
                            "is_admin": is_admin,
                        })

                response_data = {
                    "success": True,
                    "user_name": user.name,
                    "is_admin": is_admin,
                    "csrf_token": _get_spa_csrf_token(),
                    # session_id в ответе — fallback для MAX WebView, где cookie
                    # может не сохраниться из-за SameSite/CSP ограничений.
                    # Клиент устанавливает его вручную через document.cookie.
                    "session_id": request.session.sid,
                }

                response = request.make_json_response(response_data)

                # Явно проставляем session_id куку в ответ, чтобы клиент зафиксировал новую сессию.
                # samesite='None' + secure=True обязательны для MAX WebView (cross-site context),
                # иначе cookie не сохраняется при первичной аутентификации через fetch API.
                # secure включаем только для HTTPS (локальная dev-среда работает по HTTP).
                is_secure = request.httprequest.url.startswith('https')
                response.set_cookie(
                    'session_id',
                    request.session.sid,
                    max_age=90 * 86400,
                    httponly=True,
                    samesite='None',
                    secure=is_secure
                )

                return response

            except AccessDenied as e:
                if e.args == AccessDenied().args:
                    return request.make_json_response(
                        {"error": "Неверные учетные данные"}, status=400
                    )
                else:
                    return request.make_json_response(
                        {"error": e.args[0]}, status=400
                    )
            except Exception:
                _logger.exception("Login error")
                return request.make_json_response(
                    {"error": "Ошибка аутентификации"}, status=500
                )

        # GET - рендерим SPA (React router покажет LoginPage).
        # Явно передаём CSRF-токен: в голом SPA нет web-клиента Odoo, поэтому
        # кука csrf_token не проставляется, а фронт читает window.csrf_token.
        return _spa_response('rost_max_miniapp.spa_page',
                             csrf_token=_get_spa_csrf_token())

    @http.route("/rost_max/login/totp", type="http", auth="public", methods=["POST"], cors="*", csrf=False)
    def login_totp(self, **kw):
        """API: проверка 2FA кода (TOTP)."""
        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response({"error": "Invalid JSON"}, status=400)

        totp_code = body.get('totp_code')
        trusted_device = body.get('trusted_device', False)
        # csrf_token валидируется через заголовок X-CSRF-Token в _check_spa_csrf для API

        if not totp_code:
            return request.make_json_response(
                {"error": "Код обязателен"}, status=400
            )

        # Удаляем пробелы из кода
        totp_code = re.sub(r'\s', '', totp_code)

        # Получаем пользователя из pre_uid (установлен при первом логине)
        pre_uid = request.session.get('pre_uid')
        if not pre_uid:
            return request.make_json_response(
                {"error": "Сессия истекла, войдите снова"}, status=400
            )

        user = request.env['res.users'].browse(pre_uid)
        if not user.exists():
            return request.make_json_response(
                {"error": "Пользователь не найден"}, status=400
            )

        try:
            # Проверяем TOTP код
            with user._assert_can_auth(user=user.id):
                user._totp_check(int(totp_code))
        except AccessDenied as e:
            return request.make_json_response(
                {"error": str(e)}, status=400
            )
        except ValueError:
            return request.make_json_response(
                {"error": "Неверный формат кода"}, status=400
            )

        # 2FA успешно - финализируем сессию
        request.session.finalize(request.env)
        # finalize() ставит should_rotate=True — гасим, иначе sid в ответе
        # и в X-Session-Id fallback умрёт при ротации в конце запроса.
        request.session.should_rotate = False
        request.session.uid = user.id
        request.session['is_timetable_user'] = True
        request.session.pop('pre_uid', None)

        is_admin = user.has_group('base.group_system')

        response_data = {
            "success": True,
            "user_name": user.name,
            "is_admin": is_admin,
            "csrf_token": _get_spa_csrf_token(),
            # session_id в ответе — fallback для MAX WebView.
            "session_id": request.session.sid,
        }

        response = request.make_json_response(response_data)

        if trusted_device:
            _generate_trusted_device_cookie(response, user)

        # Сохраняем сессию и отправляем Cookie.
        # samesite='None' обязательно для MAX WebView (cross-site context).
        is_secure = request.httprequest.url.startswith('https')
        response.set_cookie(
            'session_id',
            request.session.sid,
            max_age=90 * 86400,
            httponly=True,
            samesite='None',
            secure=is_secure
        )

        return response

    @http.route("/rost_max/logout", type="http", auth="public", methods=["GET", "POST"])
    def logout(self):
        """Выход"""
        request.session.pop(CSRF_SESSION_KEY, None)
        request.session.logout()
        return request.redirect('/rost_max/login')

    @http.route("/rost_max/", type="http", auth="public")
    def index(self):
        """SPA: авторизационное состояние (login vs main) фронт решает сам
        по /api/user/info."""
        return _spa_response('rost_max_miniapp.spa_page',
                             csrf_token=_get_spa_csrf_token())

    def _get_user_timetable(self, user, date, faculty_id=None, batch_id=None):
        """Расписание пользователя на дату — из op.session (уроки расписания),
        как в веб-интерфейсе OpenEduCat. НЕ op.attendance.sheet: листы
        заводятся только у утверждённых уроков, а правило 629
        «Students: No Attendance Sheets» ([[0,'=',1]]) принципиально не
        даёт ученикам читать листы — на sheet-поиске от uid ученика
        расписание всегда пустое.

        Возвращает recordset op.session:
          - admin: все сессии на дату (+ фильтр faculty_id из query);
          - teacher: свои сессии (faculty_id.user_id == user.id);
          - student/parent: сессии своего класса — rule 173 «Student
            Session rule» (user_ids in user.id) сама срезает до batch'а;
          - guest: пусто.
        """
        is_admin = user.has_group('base.group_system')

        domain = [('timetable_date', '=', date)]

        if is_admin:
            if faculty_id:
                domain.append(('faculty_id', '=', int(faculty_id)))
            if batch_id:
                domain.append(('batch_id', '=', int(batch_id)))
        elif user == request.env.ref('base.public_user').sudo():
            return request.env['op.session'].browse()
        else:
            faculty = request.env['op.faculty'].sudo().search([
                ('partner_id', '=', user.partner_id.id)
            ], limit=1)
            if faculty:
                domain.append(('faculty_id.user_id', '=', user.id))
            else:
                student = request.env['op.student'].sudo().search([
                    ('partner_id', '=', user.partner_id.id)
                ], limit=1)
                if not student:
                    return request.env['op.session'].browse()
                # Без фильтра по batch: право доступа срежет до своего
                # класса (rule 173), включая случай нескольких активных
                # course_detail. Родитель видит расписание класса ребёнка
                # так же (user_ids включает user.child_ids, см. rule 173).

        return request.env['op.session'].search(domain, order='start_datetime asc')

    @http.route("/rost_max/api/timetable", type="http", auth="public", methods=["GET"])
    def api_timetable(self, date=None, faculty_id=None, batch_id=None):
        """API: список занятий на дате"""
        restore_session_if_needed()
        user = request.env.user
        date = date or fields.Date.today()
        date_str = str(date)
        is_admin = user.has_group('base.group_system')

        # batch_id игнорируется для не-админов: фильтр «класс» — чисто
        # админский инструмент, остальным роль срезает домен сама.
        lessons = self._get_user_timetable(
            user, date, faculty_id=faculty_id, batch_id=batch_id)

        # sheet_id (журнал) — только teacher/admin. Ученику/родителю журнал
        # не показываем (семантика веба), к тому же rule 629 не даёт ему
        # читать листы. IDOR-безопасно: sheet_id выдаётся только вместе с
        # правом на журнал.
        is_teacher = bool(request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)
        ], limit=1))
        sheets_map = {}
        if lessons and (is_admin or is_teacher):
            sheets_map = {
                s.session_id.id: s.id
                for s in request.env['op.attendance.sheet'].sudo().search(
                    [('session_id', 'in', lessons.ids)])
            }

        # Аватары учителей: URL на /web/image (Odoo сам ресайзит до 128x128,
        # кеширует и отдаёт плейсхолдер с первой буквой, если фото нет —
        # как в журнале урока). Наличие фото проверяем search() БЕЗ выгрузки
        # BLOB (EXISTS в SQL); URL только для залогиненных, иначе 404.
        # Список уникален: у одного учителя несколько уроков в день.
        avatar_map = {}
        if lessons and request.session.uid:
            faculty_ids = lessons.mapped('faculty_id').ids
            with_photo = request.env['op.faculty'].sudo().search(
                [('id', 'in', faculty_ids), ('image_128', '!=', False)])
            avatar_map = {
                f.id: '/web/image/op.faculty/%s/image_128/128x128' % f.id
                for f in with_photo
            }

        return request.make_json_response({
            "date": date_str,
            "is_admin": is_admin,
            "lessons": [
                {
                    "id": l.id,
                    "subject": l.subject_id.name,
                    "batch": l.batch_id.name,
                    "timing": l.timing or "",
                    "state": l.state,
                    "faculty": f"{l.faculty_id.last_name or ''} {l.faculty_id.first_name or ''} {l.faculty_id.middle_name or ''}".strip(),
                    "faculty_avatar": avatar_map.get(l.faculty_id.id, ''),
                    "sheet_id": sheets_map.get(l.id),
                }
                for l in lessons
            ]
        })

    @http.route("/rost_max/api/lesson/<int:lesson_id>/students", type="http", auth="public", methods=["GET"])
    def api_lesson_students(self, lesson_id):
        """API: список учеников урока с аватарками, оценкой и посещаемостью"""
        restore_session_if_needed()
        user = request.env.user
        sheet = request.env['op.attendance.sheet'].sudo().browse(lesson_id)
        if not sheet.exists():
            return request.make_json_response(
                {"lesson": None, "attendance_types": [], "students": []}
            )

        # IDOR-защита (журнал = sheet_id из /api/timetable): lesson_id — это
        # id op.attendance.sheet. Журнал доступен только admin/teacher —
        # семантика веба: у ученика/родителя кнопки журнала нет, их
        # собственные данные они берут через /api/my/subjects и
        # /api/my/grades. Гость тоже отсекается.
        role, own_students = _get_user_students(user)
        if role not in ('admin', 'teacher'):
            _logger.warning(
                "Security access violation: User %s (ID %s) role=%s attempted to view lesson journal ID %s",
                user.login, user.id, role, lesson_id,
            )
            return request.make_json_response(
                {"error": "Журнал доступен только учителям"}, status=403
            )
        if role == 'teacher' and sheet.faculty_id != request.env['op.faculty'].sudo().search([
                ('partner_id', '=', user.partner_id.id)], limit=1):
            _logger.warning(
                "Security access violation: User %s (ID %s) attempted to view unauthorized lesson ID %s",
                user.login, user.id, lesson_id,
            )
            return request.make_json_response(
                {"error": "Доступ к уроку запрещен"}, status=403
            )

        attend_types = request.env['op.attendance.type'].search([])
        attendance_types = [{"id": at.id, "name": at.name} for at in attend_types]

        students = []
        for ln in sheet.attendance_line:
            student = ln.student_id
            if not student:
                continue
            # Учитель/админ видят весь класс (student/parent отсечены выше).

            # Аватар: отдаём относительный URL на встроенный роутинг Odoo
            # /web/image/<model>/<id>/<field>/<W>x<H> вместо base64-строки.
            # Odoo сам ресайзит картинку на лету до 128x128, кеширует ответ
            # (Cache-Control) и отдаёт с корректным Content-Type — браузер/WebView
            # не качает бинарь заново. Бинарь из БД в JSON больше не тащим
            # (экономим RAM/CPU и режем размер ответа в разы).
            # Наличие картинки проверяем search() БЕЗ выгрузки BLOB:
            # search фильтрует по ir.rule и делает EXISTS в SQL, не читая
            # бинарное поле в память процесса. URL формируем только для
            # залогиненного юзера — иначе /web/image вернёт 404 и <img>
            # покажет broken-image вместо инициалов.
            avatar = ''
            if request.session.uid:
                if request.env['op.attendance.line'].search(
                        [('id', '=', ln.id), ('student_avatar', '!=', False)], limit=1):
                    avatar = '/web/image/op.attendance.line/%s/student_avatar/128x128' % ln.id
                elif student.avatar_1920:
                    avatar = '/web/image/op.student/%s/avatar_1920/128x128' % student.id

            last = student.last_name or ''
            first = student.first_name or ''
            middle = student.middle_name or ''
            initials = ('%s%s' % (last[:1], first[:1])).upper() if (last or first) else '?'
            name = ('%s %s %s' % (last, first, middle)).strip()

            students.append({
                "id": student.id,
                "name": name,
                "avatar": avatar,
                "initials": initials,
                "grade_1": ln.grade_1 or None,
                "grade_2": ln.grade_2 or None,
                "grade_3": ln.grade_3 or None,
                "attendance_type_id": ln.attendance_type_id.id if ln.attendance_type_id else None,
            })

        lesson = {
            "subject": sheet.subject_id.name if sheet.subject_id else '',
            "can_edit": role in ('admin', 'teacher'),
            "batch": sheet.batch_id.name if sheet.batch_id else '',
            "date": str(sheet.attendance_date) if sheet.attendance_date else '',
            "timing": sheet.timing or '',
        }

        return request.make_json_response({
            "lesson": lesson,
            "attendance_types": attendance_types,
            "students": students,
        })

    @http.route("/rost_max/api/lesson/<int:lesson_id>/save", type="http", auth="public", methods=["POST"], cors="*", csrf=False)
    def api_save_lesson(self, lesson_id, **kw):
        """API: пакетное сохранение ВСЕГО буфера журнала урока за один запрос.

        Фронт накапливает изменения локально (оценки grade_1/2/3 и
        посещаемость по каждому ученику) и шлёт их разом кнопкой "Сохранить".
        ПЕРЕЗАПИСЬ: каждая переданная колонка пишется как есть (0.0/null —
        тоже валидное значение, т.е. ластик-сброс тоже проходит). Это и есть
        механизм явного сохранения после локального редактирования.
        """
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err

        user = request.env.user
        sheet = request.env['op.attendance.sheet'].sudo().browse(lesson_id)
        if not sheet.exists():
            return request.make_json_response({"error": "Урок не найден"}, status=404)

        access_err = _check_lesson_write_access(sheet)
        if access_err:
            return access_err

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response({"error": "Invalid JSON"}, status=400)

        rows = body.get('students') or []
        if not isinstance(rows, list):
            return request.make_json_response({"error": "students должен быть массивом"}, status=400)

        written = 0
        for row in rows:
            sid = row.get('student_id')
            if not sid:
                continue
            line = request.env['op.attendance.line'].sudo().search([
                ('attendance_id', '=', lesson_id),
                ('student_id', '=', int(sid)),
            ], limit=1)
            if not line:
                continue

            vals = {}
            for gf in ('grade_1', 'grade_2', 'grade_3'):
                # Ключ ВСЕГДА прислан фронтом (полный буфер). null/'' = сброс
                # в 0.0 (на чтении /students вернёт ln.grade_1 or None => «-»).
                if gf not in row:
                    continue
                g = row[gf]
                if g is None or g == '':
                    vals[gf] = 0.0
                else:
                    try:
                        vals[gf] = float(g)
                    except (ValueError, TypeError):
                        pass
            # attendance_type_id: ключ может быть прислан явно (в т.ч. null/'' = сброс)
            if 'attendance_type_id' in row:
                att = row['attendance_type_id']
                vals['attendance_type_id'] = (int(att) if att not in (None, '') else False)

            if vals:
                line.write(vals)
                written += 1

        return request.make_json_response({"success": True, "written": written})

    @http.route("/rost_max/api/user/info", type="http", auth="public", methods=["GET"])
    def api_user_info(self):
        """API: получение информации о текущем пользователе и его ролях"""
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')

        is_teacher = bool(request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)
        ], limit=1))

        is_student = bool(request.env['op.student'].sudo().search([
            ('partner_id', '=', user.partner_id.id)
        ], limit=1))

        is_parent = bool(request.env['op.parent'].sudo().search([
            ('name', '=', user.partner_id.id)
        ], limit=1))

        return request.make_json_response({
            "user_name": user.name,
            "is_admin": is_admin,
            "is_teacher": is_teacher,
            "is_student": is_student,
            "is_parent": is_parent,
        })

    @http.route("/rost_max/api/dashboard_info", type="http", auth="public", methods=["GET"])
    def api_dashboard_info(self, date=None, **kw):
        """API: сбор статистики для дашборда с умным поиском даты"""
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)
        student = request.env['op.student'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)

        # 1. Определение целевой даты
        date_str = date or str(fields.Date.today())
        date_val = fields.Date.from_string(date_str)
        is_fallback = False
        fallback_date = ""

        # Проверяем, есть ли уроки на выбранную дату (op.session — см.
        # docstring _get_user_timetable: sheet недоступен ученикам, rule 629)
        sessions = self._get_user_timetable(user, date_val)
        if not sessions:
            # На выбранную дату уроков нет (лето/выходной). Ищем последний
            # активный день в истории
            domain = [('state', '!=', 'cancel')]
            if not is_admin:
                if faculty:
                    domain.append(('faculty_id.user_id', '=', user.id))
                elif student:
                    # Право доступа (rule 173) само срежет до класса
                    # ребёнка/ученика — домен не сужаем, ищем дату.
                    pass
                else:
                    domain.append(('id', '=', 0))  # пустой результат

            last_session = request.env['op.session'].sudo().search(
                domain, order='timetable_date desc', limit=1)
            if last_session:
                date_val = last_session.timetable_date
                date_str = str(date_val)
                is_fallback = True
                fallback_date = date_str
                sessions = self._get_user_timetable(user, date_val)

        # 2. Расчет показателей на целевую дату
        metrics = {}
        next_lesson = None

        if sessions:
            first_session = sessions[0]  # отсортированы по start_datetime
            # Кабинет читаем через sudo: у ученика нет ACL на op.classroom
            room = first_session.classroom_id.sudo().name if first_session.classroom_id else None
            next_lesson = {
                "id": first_session.id,
                "subject": first_session.subject_id.name if first_session.subject_id else "Урок",
                "batch": first_session.batch_id.name if first_session.batch_id else "",
                "time": first_session.timing or "12:15 - 13:00",
                "room": room or "Кабинет"
            }

        if is_admin:
            # Журналы (листы) нужны админу для статистики посещаемости
            sheets = request.env['op.attendance.sheet'].sudo().search([
                ('session_id', 'in', sessions.ids)])
            lines = sheets.mapped('attendance_line')
            total_lines = len(lines)
            attendance_pct = 100.0
            if total_lines > 0:
                present = len(lines.filtered(lambda l: l.attendance_type_id and 'absent' not in (l.attendance_type_id.name or '').lower() and 'отсутств' not in (l.attendance_type_id.name or '').lower() and 'нет' not in (l.attendance_type_id.name or '').lower()))
                attendance_pct = round((present / total_lines) * 100, 1)

            unfilled = len(sheets.filtered(lambda s: any(not l.attendance_type_id for l in s.attendance_line)))
            metrics = {
                "active_lessons": len(sessions),
                "unfilled_sheets": unfilled,
                "attendance_pct": attendance_pct,
                "total_students": len(lines.mapped('student_id')),
                "pending_substitutes": 0
            }
        elif faculty:
            # Журналы только своих уроков (листы из confirm-сессий)
            sheets = request.env['op.attendance.sheet'].sudo().search([
                ('session_id', 'in', sessions.ids)])
            lines = sheets.mapped('attendance_line')
            total_lines = len(lines)
            attendance_pct = 100.0
            if total_lines > 0:
                present = len(lines.filtered(lambda l: l.attendance_type_id and 'absent' not in (l.attendance_type_id.name or '').lower() and 'отсутств' not in (l.attendance_type_id.name or '').lower() and 'нет' not in (l.attendance_type_id.name or '').lower()))
                attendance_pct = round((present / total_lines) * 100, 1)

            graded = len(lines.filtered(lambda l: l.grade_1 > 0))
            metrics = {
                "total_lessons": len(sessions),
                "completed_lessons": len(sheets.filtered(lambda s: any(l.attendance_type_id for l in s.attendance_line))),
                "attendance_pct": attendance_pct,
                "graded_count": graded
            }
        elif student:
            # Для студента считаем общий GPA за всё время
            all_grades = request.env['op.attendance.line'].sudo().search([
                ('student_id', '=', student.id),
                ('grade_1', '>', 0)
            ]).mapped('grade_1')
            gpa = round(sum(all_grades) / len(all_grades), 2) if all_grades else 4.5
            metrics = {
                "gpa": gpa,
                "pending_homework": len(sessions)  # условная цифра уроков за день
            }

        return request.make_json_response({
            "is_admin": is_admin,
            "is_teacher": bool(faculty),
            "is_student": bool(student),
            "date": date_str,
            "is_fallback": is_fallback,
            "fallback_date": fallback_date,
            "metrics": metrics,
            "next_lesson": next_lesson,
            **self._dashboard_feed(user, is_admin, faculty, student, sessions, date_val),
        })

    # --- ЛЕНТА ДНЯ (вариант A) ---------------------------------------------

    def _dashboard_feed(self, user, is_admin, faculty, student, sessions, date_val):
        """Лента дня: уроки с бейджами + роль-специфичные блоки.

        Общий агрегат для ученика/родителя, учителя и админа (макеты
        design/dashboard-variants.html и dashboard-teacher-admin.html).
        Все чтения через sudo с жёсткой ролевой фильтрацией (IDOR по
        построению): ученик — только свои оценки/ДЗ своего класса,
        учитель — только свои уроки/задания.
        """
        now = fields.Datetime.now()
        role, own_students = _get_user_students(user)

        # --- Лента уроков (все роли) ---
        sheets_map = {}
        if sessions:
            sheets_map = {
                s.session_id.id: s for s in request.env[
                    'op.attendance.sheet'].sudo().search(
                    [('session_id', 'in', sessions.ids)])
            }
        lessons_feed = []
        for l in sessions:
            sheet = sheets_map.get(l.id)
            unfilled = bool(sheet) and any(
                not ln.attendance_type_id for ln in sheet.attendance_line)
            hw = (sheet.lesson_homework or '').strip() if sheet else ''
            lessons_feed.append({
                "id": l.id,
                "sheet_id": sheet.id if sheet else None,
                "subject": l.subject_id.name if l.subject_id else "Урок",
                "batch": self._batch_short(l.batch_id.name) if l.batch_id else "",
                "faculty": self._faculty_name(l.faculty_id),
                "timing": l.timing or "",
                "start": str(l.start_datetime) if l.start_datetime else "",
                "end": str(l.end_datetime) if l.end_datetime else "",
                "is_now": bool(
                    l.start_datetime and l.end_datetime
                    and l.start_datetime <= now <= l.end_datetime
                    and l.state not in ('cancel', 'done')),
                "journal_unfilled": unfilled,
                "homework": hw,
            })

        feed = {"lessons": lessons_feed}

        # --- Ученик / родитель: оценки за сегодня + ДЗ ---
        if role in ('student', 'parent') and own_students:
            today_lines = request.env['op.attendance.line'].sudo().search([
                ('student_id', 'in', own_students.ids),
                ('attendance_date', '=', date_val),
            ], order='attendance_date asc, id asc')
            grades_today = []
            for ln in today_lines:
                grades = [int(g) for g in (ln.grade_1, ln.grade_2, ln.grade_3)
                          if g and g > 0]
                if grades:
                    grades_today.append({
                        "grades": grades,
                        "subject": ln.subject_id.name if ln.subject_id else "",
                        "comment": ln.remark or ln.lesson_topic or "",
                    })
            feed["grades_today"] = grades_today

            batches = own_students.mapped('active_batch_id')
            asgs = request.env['op.assignment'].sudo().search([
                ('state', '=', 'publish'),
                ('batch_id', 'in', batches.ids),
                ('submission_date', '>=', fields.Datetime.now() - timedelta(days=21)),
            ], order='submission_date asc')
            subs = request.env['op.assignment.sub.line'].sudo().search([
                ('assignment_id', 'in', asgs.ids),
                ('student_id', 'in', own_students.ids),
            ])
            done_ids = {s.assignment_id.id for s in subs
                        if s.state in ('submit', 'accept')}
            feed["homework"] = [{
                "id": a.id,
                "subject": a.subject_id.name if a.subject_id else "",
                "task": tools.html2plaintext(a.description) or a.name,
                "due": str(a.submission_date) if a.submission_date else "",
                "overdue": bool(a.submission_date and a.submission_date < now),
                "done": a.id in done_ids,
            } for a in asgs]

        # --- Учитель: журналы к заполнению + задано моими уроками ---
        if role == 'teacher' and faculty:
            to_fill = []
            for l in sessions:
                sheet = sheets_map.get(l.id)
                if sheet and any(
                        not ln.attendance_type_id
                        for ln in sheet.attendance_line):
                    to_fill.append({
                        "sheet_id": sheet.id,
                        "subject": l.subject_id.name if l.subject_id else "",
                        "batch": self._batch_short(l.batch_id.name) if l.batch_id else "",
                        "timing": l.timing or "",
                        "room": l.classroom_id.sudo().name or "",
                        "students": len(sheet.attendance_line),
                    })
            feed["journals_to_fill"] = to_fill

            my_asgs = request.env['op.assignment'].sudo().search([
                ('faculty_id', '=', faculty.id),
                ('state', '=', 'publish'),
                ('submission_date', '>=', fields.Datetime.now() - timedelta(days=21)),
            ], order='submission_date asc')
            submitted_counts = {
                s['assignment_id'][0]: s['__count']
                for s in request.env['op.assignment.sub.line'].sudo().read_group(
                    [('assignment_id', 'in', my_asgs.ids),
                     ('state', 'in', ['submit', 'accept'])],
                    ['assignment_id'], ['assignment_id'])
            }
            feed["my_homework"] = [{
                "id": a.id,
                "subject": a.subject_id.name if a.subject_id else "",
                "batch": self._batch_short(a.batch_id.name) if a.batch_id else "",
                "task": tools.html2plaintext(a.description) or a.name,
                "due": str(a.submission_date) if a.submission_date else "",
                "submitted": submitted_counts.get(a.id, 0),
                "total": len(a.allocation_ids),
            } for a in my_asgs]

        # --- Админ: полоса цифр + требует внимания ---
        if role == 'admin':
            all_sheets = list(sheets_map.values())
            unfilled_sheets = [s for s in all_sheets if any(
                not ln.attendance_type_id for ln in s.attendance_line)]
            morning_passed = sum(
                1 for s in unfilled_sheets
                if s.session_id.end_datetime and s.session_id.end_datetime < now)
            alerts = []
            if unfilled_sheets:
                alerts.append({
                    "kind": "journals",
                    "count": len(unfilled_sheets),
                    "morning_passed": morning_passed,
                })
            feed["admin_stats"] = {
                "lessons_today": len(sessions),
                "batches_today": len(sessions.mapped('batch_id')),
                "journals_unfilled": len(unfilled_sheets),
            }
            feed["alerts"] = alerts

        return feed

    @staticmethod
    def _batch_short(name):
        """«5А  2026/2027» -> «5А»: отбрасываем учебный год в имени класса."""
        return re.sub(r'\s*\d{4}/\d{4}\s*$', '', name or '').strip()

    @staticmethod
    def _faculty_name(f):
        if not f:
            return ""
        return f"{f.last_name or ''} {f.first_name or ''} {f.middle_name or ''}".strip()


    @http.route("/rost_max/api/faculties", type="http", auth="public", methods=["GET"])
    def api_faculties(self):
        """API: список учителей (только для админа)"""
        restore_session_if_needed()
        user = request.env.user
        if not user.has_group('base.group_system'):
            return request.make_json_response({"faculties": []})

        faculties = request.env['op.faculty'].search([], order='last_name,first_name')
        return request.make_json_response({
            "faculties": [
                {
                    "id": f.id,
                    "name": f"{f.last_name or ''} {f.first_name or ''} {f.middle_name or ''}".strip()
                }
                for f in faculties
            ]
        })

    @http.route("/rost_max/api/batches", type="http", auth="public", methods=["GET"])
    def api_batches(self):
        """API: список классов (только для админа)"""
        restore_session_if_needed()
        user = request.env.user
        if not user.has_group('base.group_system'):
            return request.make_json_response({"batches": []})

        batches = request.env['op.batch'].search([], order='sequence, name')
        return request.make_json_response({
            "batches": [
                {"id": b.id, "name": b.name}
                for b in batches
            ]
        })

    # --- УСПЕВАЕМОСТЬ (ученик / родитель) ---

    def _get_quarter_terms(self):
        """Четверти: {1..4: op.academic.term} ТЕКУЩЕГО учебного года.
        Логика как в op.subject.grades._compute_line_ids — четверти это
        дочерние термины (parent_term != False), номер = цифра в названии.
        Обязательный фильтр по году: «1 четверть» существует у каждого
        op.academic.year, без него q_map[1] ловит первый попавшийся (вчерашний).
        Год определяется по дате (образец: op.session._compute_academic_year).
        """
        today = fields.Date.today()
        year = request.env['op.academic.year'].sudo().search([
            ('start_date', '<=', today), ('end_date', '>=', today)
        ], limit=1)
        domain = [('parent_term', '!=', False)]
        if year:
            domain.append(('academic_year_id', '=', year.id))
        terms = request.env['op.academic.term'].sudo().search(domain)
        q_map = {}
        for i in range(1, 5):
            t = terms.filtered(lambda x, n=i: str(n) in (x.name or ''))
            if t:
                q_map[i] = t[0]
        return q_map

    def _get_current_quarter(self, q_map):
        """Номер текущей четверти по дате (как _get_current_q_code в модели)."""
        today = fields.Date.today()
        for i in sorted(q_map):
            term = q_map[i]
            if term.term_start_date <= today <= term.term_end_date:
                return i
        started = [i for i in sorted(q_map) if q_map[i].term_start_date <= today]
        return started[-1] if started else 1

    @staticmethod
    def _line_payload(ln):
        """Сериализация op.attendance.line для read-only экранов."""
        grades = [int(g) for g in (ln.grade_1, ln.grade_2, ln.grade_3) if g and g > 0]
        return {
            "line_id": ln.id,
            "date": str(ln.attendance_date) if ln.attendance_date else '',
            "subject_id": ln.subject_id.id if ln.subject_id else None,
            "subject": ln.subject_id.name if ln.subject_id else '',
            "grades": grades,
            "attendance_type_id": ln.attendance_type_id.id if ln.attendance_type_id else None,
            "attendance": ln.attendance_type_id.name if ln.attendance_type_id else None,
            "remark": ln.remark or '',
            "topic": ln.lesson_topic or '',
        }

    @http.route("/rost_max/api/my/subjects", type="http", auth="public", methods=["GET"])
    def api_my_subjects(self, quarter=None):
        """API: предметы с оценками/посещаемостью для ученика и родителя.

        Считается НА ЛЕТУ из op.attendance.line (не из stored-компутов
        op.subject.grades), чтобы успеваемость всегда совпадала с журналом.
        Доступ жёстко ограничен своими учениками (IDOR по построению).
        """
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        role, own_students = _get_user_students(user)
        if role not in ('student', 'parent') or not own_students:
            return request.make_json_response(
                {"error": "Доступно только ученикам и родителям"}, status=403)

        q_map = self._get_quarter_terms()
        current_q = self._get_current_quarter(q_map)
        try:
            q = int(quarter) if quarter else current_q
        except ValueError:
            q = current_q
        if q not in q_map:
            return request.make_json_response(
                {"error": "Четверть не найдена"}, status=404)

        term = q_map[q]
        lines = request.env['op.attendance.line'].sudo().search([
            ('student_id', 'in', own_students.ids),
            ('attendance_date', '>=', term.term_start_date),
            ('attendance_date', '<=', term.term_end_date),
        ])

        # Группируем ученик x предмет, статистика через движок get_stats_from_lines
        students_payload = []
        stat_obj = request.env['op.attendance.line']
        for st in own_students:
            st_lines = request.env['op.attendance.line'].sudo().search([
                ('student_id', '=', st.id),
                ('attendance_date', '>=', term.term_start_date),
                ('attendance_date', '<=', term.term_end_date),
            ])
            by_subject = {}
            for ln in st_lines:
                by_subject.setdefault(ln.subject_id, request.env['op.attendance.line'].browse())
            for ln in st_lines:
                by_subject[ln.subject_id] |= ln

            subjects = []
            for subj, subj_lines in by_subject.items():
                if not subj:
                    continue
                stats = stat_obj.get_stats_from_lines(subj_lines)
                subjects.append({
                    "subject_id": subj.id,
                    "name": subj.name,
                    "average_mark": stats['avg'],
                    "attendance_rate": stats['rate'],
                    "total_classes": stats['total'],
                    "present_classes": stats['present'],
                    "last_remark": stats['last_remark'],
                    "counts": {str(k): v for k, v in stats['counts'].items()},
                })
            subjects.sort(key=lambda s: s['name'])
            students_payload.append({
                "student_id": st.id,
                "name": ("%s %s %s" % (st.last_name or '', st.first_name or '', st.middle_name or '')).strip(),
                "subjects": subjects,
            })

        return request.make_json_response({
            "quarter": q,
            "current_quarter": current_q,
            "quarters": [{"q": i, "name": q_map[i].name} for i in sorted(q_map)],
            "students": students_payload,
        })

    @http.route("/rost_max/api/my/grades/<int:subject_id>", type="http", auth="public", methods=["GET"])
    def api_my_grades(self, subject_id, quarter=None, **kw):
        """API: хронология оценок/посещаемости ученика по предмету за четверть."""
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        role, own_students = _get_user_students(user)
        if role not in ('student', 'parent') or not own_students:
            return request.make_json_response(
                {"error": "Доступно только ученикам и родителям"}, status=403)

        q_map = self._get_quarter_terms()
        current_q = self._get_current_quarter(q_map)
        try:
            q = int(quarter) if quarter else current_q
        except ValueError:
            q = current_q
        if q not in q_map:
            return request.make_json_response(
                {"error": "Четверть не найдена"}, status=404)

        term = q_map[q]
        lines = request.env['op.attendance.line'].sudo().search([
            ('student_id', 'in', own_students.ids),
            ('subject_id', '=', subject_id),
            ('attendance_date', '>=', term.term_start_date),
            ('attendance_date', '<=', term.term_end_date),
        ], order='attendance_date desc')

        stats = request.env['op.attendance.line'].get_stats_from_lines(lines)
        return request.make_json_response({
            "quarter": q,
            "subject_id": subject_id,
            "summary": {
                "average_mark": stats['avg'],
                "attendance_rate": stats['rate'],
                "total_classes": stats['total'],
                "present_classes": stats['present'],
                "counts": {str(k): v for k, v in stats['counts'].items()},
                "last_remark": stats['last_remark'],
            },
            "lines": [self._line_payload(ln) for ln in lines],
        })