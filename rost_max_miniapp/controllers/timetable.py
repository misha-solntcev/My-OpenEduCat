# -*- coding: utf-8 -*-
import secrets
import re
import base64
from odoo import http
from odoo.http import request
from odoo import fields
import logging
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

# Ключ сессии для нашего стабильного CSRF-токена (без o<timestamp>, в отличие
# от session['csrf_token'] Odoo). Токен создаётся лениво и не меняется в рамках
# сессии -> детерминированное сравнение на POST (без хрупкости time-suffixed
# формата Odoo, который ломался при разнице времени рендера и отправки).
CSRF_SESSION_KEY = 'spa_csrf_token'

# Trusted device cookie name (совпадает с auth_totp)
TRUSTED_DEVICE_COOKIE = 'td_id'
TRUSTED_DEVICE_AGE = 90 * 86400  # 90 days


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
                }

                response = request.make_json_response(response_data)

                # Явно проставляем session_id куку в ответ, чтобы клиент зафиксировал новую сессию
                response.set_cookie(
                    'session_id',
                    request.session.sid,
                    max_age=90 * 86400,
                    httponly=True,
                    samesite='Lax'
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
        return request.render('rost_max_miniapp.spa_page',
                               {'csrf_token': _get_spa_csrf_token()})

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
        request.session.uid = user.id
        request.session['is_timetable_user'] = True
        request.session.pop('pre_uid', None)

        is_admin = user.has_group('base.group_system')

        response_data = {
            "success": True,
            "user_name": user.name,
            "is_admin": is_admin,
            "csrf_token": _get_spa_csrf_token(),
        }

        response = request.make_json_response(response_data)

        if trusted_device:
            _generate_trusted_device_cookie(response, user)

        # Сохраняем сессию и отправляем Cookie
        response.set_cookie(
            'session_id',
            request.session.sid,
            max_age=90 * 86400,
            httponly=True,
            samesite='Lax'
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
        """Главная - редирект на login или dashboard"""
        if request.session.get('is_timetable_user'):
            return request.redirect('/rost_max/dashboard')
        return request.redirect('/rost_max/login')

    @http.route("/rost_max/dashboard", type="http", auth="public")
    def dashboard_page(self):
        """Дашборд - рендерит SPA (React router покажет DashboardPage)"""
        return request.render('rost_max_miniapp.spa_page',
                              {'csrf_token': _get_spa_csrf_token()})

    @http.route("/rost_max/timetable", type="http", auth="public")
    def timetable_page(self):
        """Страница расписания - рендерит SPA"""
        return request.render('rost_max_miniapp.spa_page',
                              {'csrf_token': _get_spa_csrf_token()})

    @http.route("/rost_max/lesson/<int:lesson_id>", type="http", auth="public")
    def lesson_page(self, lesson_id):
        """Страница журнала урока - рендерит SPA"""
        return request.render('rost_max_miniapp.spa_page',
                              {'csrf_token': _get_spa_csrf_token()})

    @http.route("/rost_max/modules", type="http", auth="public")
    def modules_page(self):
        """Страница модулей - рендерит тот же SPA (клиентский роутер покажет экран)"""
        return request.render('rost_max_miniapp.spa_page',
                              {'csrf_token': _get_spa_csrf_token()})

    def _get_user_timetable(self, user, date, faculty_id=None):
        """Получить timetable для пользователя по дате и факультету (админ)"""
        is_admin = user.has_group('base.group_system')
        
        domain = [('attendance_date', '=', date)]
        
        if is_admin and faculty_id:
            domain.append(('faculty_id', '=', int(faculty_id)))
        elif is_admin:
            pass  # админ видит все
        elif user == request.env.ref('base.public_user').sudo():
            # Гость - пустой результат
            return request.env['op.attendance.sheet'].browse()
        else:
            faculty = request.env['op.faculty'].sudo().search([
                ('partner_id', '=', user.partner_id.id)
            ], limit=1)
            if faculty:
                domain.append(('faculty_id', '=', faculty.id))
            else:
                student = request.env['op.student'].sudo().search([
                    ('partner_id', '=', user.partner_id.id)
                ], limit=1)
                # У op.student нет прямого batch_id — он через
                # course_detail_ids (op.student.course.batch_id).
                if student:
                    batch = student.course_detail_ids.mapped('batch_id')[:1]
                    if batch:
                        domain.append(('batch_id', '=', batch.id))
                    else:
                        return request.env['op.attendance.sheet'].browse()
                else:
                    return request.env['op.attendance.sheet'].browse()

        return request.env['op.attendance.sheet'].search(domain)

    @http.route("/rost_max/api/timetable", type="http", auth="public", methods=["GET"])
    def api_timetable(self, date=None, faculty_id=None):
        """API: список занятий на дате"""
        user = request.env.user
        date = date or fields.Date.today()
        date_str = str(date)
        is_admin = user.has_group('base.group_system')

        lessons = self._get_user_timetable(user, date, faculty_id).sudo()

        return request.make_json_response({
            "date": date_str,
            "is_admin": is_admin,
            "lessons": [
                {
                    "id": l.id,
                    "subject": l.subject_id.name,
                    "batch": l.batch_id.name,
                    "timing": l.timing or "",
                    "faculty": f"{l.session_id.faculty_id.last_name or ''} {l.session_id.faculty_id.first_name or ''} {l.session_id.faculty_id.middle_name or ''}".strip()
                }
                for l in lessons
            ]
        })

    @http.route("/rost_max/api/lesson/<int:lesson_id>/students", type="http", auth="public", methods=["GET"])
    def api_lesson_students(self, lesson_id):
        """API: список учеников урока с аватарками, оценками и посещаемостью"""
        user = request.env.user
        sheet = request.env['op.attendance.sheet'].sudo().browse(lesson_id)
        if not sheet.exists():
            return request.make_json_response(
                {"lesson": None, "attendance_types": [], "students": []}
            )

        # IDOR-защита: закрытый урок отдаём только админу либо тому, у кого
        # он реально есть в расписании (студент своей группы / преподаватель).
        # Гость (public_user) в allowed_sheets не попадёт -> 403.
        is_admin = user.has_group('base.group_system')
        if not is_admin:
            allowed_sheets = self._get_user_timetable(user, sheet.attendance_date).sudo()
            if sheet not in allowed_sheets:
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

        return request.make_json_response({
            "user_name": user.name,
            "is_admin": is_admin,
            "is_teacher": is_teacher,
            "is_student": is_student,
        })

    @http.route("/rost_max/api/dashboard_info", type="http", auth="public", methods=["GET"])
    def api_dashboard_info(self, date=None, **kw):
        """API: сбор статистики для дашборда с умным поиском даты"""
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

        # Проверяем, есть ли уроки на выбранную дату
        sheets = self._get_user_timetable(user, date_val).sudo()
        if not sheets:
            # На выбранную дату уроков нет (лето/выходной). Ищем последний активный день в истории
            domain = []
            if not is_admin:
                if faculty:
                    domain.append(('faculty_id', '=', faculty.id))
                elif student:
                    batch = student.course_detail_ids.mapped('batch_id')[:1]
                    if batch:
                        domain.append(('batch_id', '=', batch.id))
                    else:
                        domain.append(('id', '=', 0))  # пустой результат

            last_sheet = request.env['op.attendance.sheet'].sudo().search(domain, order='attendance_date desc', limit=1)
            if last_sheet:
                date_val = last_sheet.attendance_date
                date_str = str(date_val)
                is_fallback = True
                fallback_date = date_str
                sheets = self._get_user_timetable(user, date_val).sudo()

        # 2. Расчет показателей на целевую дату
        metrics = {}
        next_lesson = None

        if sheets:
            # Сортируем уроки по времени, чтобы определить первый/ближайший
            sorted_sheets = sheets.sorted(key=lambda s: s.timing or '')
            first_sheet = sorted_sheets[0]
            next_lesson = {
                "id": first_sheet.id,
                "subject": first_sheet.subject_id.name if first_sheet.subject_id else "Урок",
                "batch": first_sheet.batch_id.name if first_sheet.batch_id else "",
                "time": first_sheet.timing or "12:15 - 13:00",
                "room": "Кабинет"
            }

        if is_admin:
            lines = sheets.mapped('attendance_line')
            total_lines = len(lines)
            attendance_pct = 100.0
            if total_lines > 0:
                present = len(lines.filtered(lambda l: l.attendance_type_id and 'absent' not in (l.attendance_type_id.name or '').lower() and 'отсутств' not in (l.attendance_type_id.name or '').lower() and 'нет' not in (l.attendance_type_id.name or '').lower()))
                attendance_pct = round((present / total_lines) * 100, 1)

            unfilled = len(sheets.filtered(lambda s: any(not l.attendance_type_id for l in s.attendance_line)))
            metrics = {
                "active_lessons": len(sheets),
                "unfilled_sheets": unfilled,
                "attendance_pct": attendance_pct,
                "total_students": len(lines.mapped('student_id')),
                "pending_substitutes": 0
            }
        elif faculty:
            lines = sheets.mapped('attendance_line')
            total_lines = len(lines)
            attendance_pct = 100.0
            if total_lines > 0:
                present = len(lines.filtered(lambda l: l.attendance_type_id and 'absent' not in (l.attendance_type_id.name or '').lower() and 'отсутств' not in (l.attendance_type_id.name or '').lower() and 'нет' not in (l.attendance_type_id.name or '').lower()))
                attendance_pct = round((present / total_lines) * 100, 1)

            graded = len(lines.filtered(lambda l: l.grade_1 > 0))
            metrics = {
                "total_lessons": len(sheets),
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
                "pending_homework": len(sheets)  # условная цифра уроков за день
            }

        return request.make_json_response({
            "is_admin": is_admin,
            "is_teacher": bool(faculty),
            "is_student": bool(student),
            "date": date_str,
            "is_fallback": is_fallback,
            "fallback_date": fallback_date,
            "metrics": metrics,
            "next_lesson": next_lesson
        })

    @http.route("/rost_max/api/faculties", type="http", auth="public", methods=["GET"])
    def api_faculties(self):
        """API: список учителей (только для админа)"""
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