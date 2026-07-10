# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
import logging

_logger = logging.getLogger(__name__)


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

            email = body.get('email')
            password = body.get('password')

            if not email or not password:
                return request.make_json_response(
                    {"error": "Email и пароль обязательны"}, status=400
                )

            try:
                credential = {'login': email, 'password': password, 'type': 'password'}
                auth_info = request.session.authenticate(request.db, credential)
                if not auth_info.get('uid'):
                    return request.make_json_response(
                        {"error": "Неверные учетные данные"}, status=400
                    )
                request.session['is_timetable_user'] = True
                user = request.env['res.users'].browse(auth_info['uid'])
                is_admin = user.has_group('base.group_system')
                return request.make_json_response(
                    {"success": True, "user_name": user.name, "is_admin": is_admin}
                )
            except Exception:
                return request.make_json_response(
                    {"error": "Ошибка аутентификации"}, status=500
                )

        # GET - рендерим SPA (React router покажет LoginPage)
        return request.render('rost_max_miniapp.spa_page')

    @http.route("/rost_max/logout", type="http", auth="public", methods=["GET", "POST"])
    def logout(self):
        """Выход"""
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
        return request.render('rost_max_miniapp.spa_page')

    @http.route("/rost_max/timetable", type="http", auth="public")
    def timetable_page(self):
        """Страница расписания - рендерит SPA"""
        return request.render('rost_max_miniapp.spa_page')

    @http.route("/rost_max/lesson/<int:lesson_id>", type="http", auth="public")
    def lesson_page(self, lesson_id):
        """Страница журнала урока - рендерит SPA"""
        return request.render('rost_max_miniapp.spa_page')

    @http.route("/rost_max/modules", type="http", auth="public")
    def modules_page(self):
        """Страница модулей - рендерит тот же SPA (клиентский роутер покажет экран)"""
        return request.render('rost_max_miniapp.spa_page')

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
            faculty = request.env['op.faculty'].search([
                ('partner_id', '=', user.partner_id.id)
            ], limit=1)
            if faculty:
                domain.append(('faculty_id', '=', faculty.id))
            else:
                student = request.env['op.student'].search([
                    ('partner_id', '=', user.partner_id.id)
                ], limit=1)
                if student and student.batch_id:
                    domain.append(('batch_id', '=', student.batch_id.id))
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
                elif request.env['op.student'].search(
                        [('id', '=', student.id), ('avatar_1920', '!=', False)], limit=1):
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
                "grade": ln.grade_1 or None,
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

    @http.route("/rost_max/api/lesson/<int:lesson_id>/update", type="http", auth="public", methods=["POST"], cors="*", csrf=False)
    def api_update_lesson_student(self, lesson_id, **kw):
        """API: сохранение оценки и/или отметки посещаемости ученика в строке посещаемости"""
        # Ручная валидация CSRF для JSON POST: системный валидатор Odoo для
        # http-роутов ищет токен только в query/form-data, а фронт шлёт его
        # в заголовке X-CSRF-Token (JSON-тело не парсится до проверки).
        csrf_token = request.httprequest.headers.get('X-CSRF-Token')
        if not request.validate_csrf(csrf_token):
            return request.make_json_response({"error": "CSRF validation failed"}, status=400)

        user = request.env.user
        sheet = request.env['op.attendance.sheet'].sudo().browse(lesson_id)
        if not sheet.exists():
            return request.make_json_response({"error": "Урок не найден"}, status=404)

        # Защита от фальсификации оценок: писать может только админ либо
        # преподаватель, назначенный вести этот урок. Гость/студент/чужой
        # преподаватель получают 403.
        is_admin = user.has_group('base.group_system')
        if not is_admin:
            faculty = request.env['op.faculty'].sudo().search([
                ('partner_id', '=', user.partner_id.id)
            ], limit=1)
            if not faculty or sheet.faculty_id != faculty:
                _logger.warning(
                    "Security write violation: User %s (ID %s) attempted to write grades on unauthorized lesson ID %s",
                    user.login, user.id, lesson_id,
                )
                return request.make_json_response(
                    {"error": "У вас нет прав для изменения оценок этого урока"}, status=403
                )

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400
            )

        student_id = body.get('student_id')
        if not student_id:
            return request.make_json_response(
                {"error": "student_id обязателен"}, status=400
            )

        line = request.env['op.attendance.line'].sudo().search([
            ('attendance_id', '=', lesson_id),
            ('student_id', '=', int(student_id)),
        ], limit=1)
        if not line:
            return request.make_json_response(
                {"error": "Строка посещаемости не найдена"}, status=404
            )

        vals = {}
        grade = body.get('grade')
        if grade is not None:
            if grade == '' or grade is None:
                vals['grade_1'] = 0.0
            else:
                try:
                    vals['grade_1'] = float(grade)
                except (ValueError, TypeError):
                    pass

        attendance_type_id = body.get('attendance_type_id')
        if attendance_type_id not in (None, ''):
            vals['attendance_type_id'] = int(attendance_type_id)

        if vals:
            line.write(vals)

        return request.make_json_response({"success": True})

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