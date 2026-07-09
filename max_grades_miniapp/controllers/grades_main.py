# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo import fields
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)


class MaxGradesController(http.Controller):
    
    @http.route("/max/grades/login", type="http", auth="none", methods=["GET", "POST"], cors="*", csrf=False)
    def login(self, email=None, password=None, redirect="/max/grades/dashboard", **kw):
        """Страница входа и обработка аутентификации"""
        if request.httprequest.method == 'POST':
            body = {}
            if request.httprequest.data:
                try:
                    body = json.loads(request.httprequest.data.decode('utf-8'))
                except Exception:
                    pass
            if 'params' in body:
                body = body.get('params', {})
            email = body.get('email') or email
            password = body.get('password') or password

            if not email or not password:
                return request.make_response(
                    json.dumps({"error": "Email и пароль обязательны"}),
                    headers=[('Content-Type', 'application/json')]
                )

            try:
                credential = {'login': email, 'password': password, 'type': 'password'}
                auth_info = request.session.authenticate(request.db, credential)
                if not auth_info.get('uid'):
                    return request.make_response(
                        json.dumps({"error": "Неверные учетные данные"}),
                        headers=[('Content-Type', 'application/json')]
                    )
                
                request.session['is_grades_user'] = True
                user = request.env['res.users'].browse(auth_info['uid'])
                return request.make_response(
                    json.dumps({"success": True, "user_name": user.name}),
                    headers=[('Content-Type', 'application/json')]
                )
            except Exception as e:
                _logger.exception("Authentication error for user %s", email)
                return request.make_response(
                    json.dumps({"error": "Ошибка аутентификации"}),
                    headers=[('Content-Type', 'application/json')]
                )

        return request.render('max_grades_miniapp.max_grades_login_page')

    @http.route("/max/grades/logout", type="http", auth="user", methods=["GET", "POST"])
    def logout(self):
        """Выход из системы"""
        request.session.logout()
        return request.redirect('/max/grades/login')

    @http.route("/max/grades/dashboard", type="http", auth="user")
    def dashboard_page(self):
        """Дашборд с модулями"""
        modules = [
            {"id": "schedule", "name": "Расписание", "icon": "fa-calendar"},
            {"id": "grades", "name": "Оценки", "icon": "fa-star"},
            {"id": "attendance", "name": "Посещаемость", "icon": "fa-check"}
        ]
        return request.render('max_grades_miniapp.max_grades_dashboard_page', {
            'modules': modules
        })

    @http.route("/max/grades/lessons", type="http", auth="user")
    def lessons_page(self, date_filter=None):
        """Страница со списком уроков"""
        today_str = fields.Date.today()
        user = request.env.user
        is_admin = user.has_group('base.group_system')

        faculties = []
        if is_admin:
            faculties = request.env["op.faculty"].search([])

        return request.render('max_grades_miniapp.max_grades_lessons_page', {
            'today_str': today_str,
            'is_admin': is_admin,
            'faculties': faculties
        })

    @http.route("/max/grades/lesson/<int:lesson_id>", type="http", auth="user")
    def lesson_students_page(self, lesson_id):
        """Страница с студентами и оценками для урока"""
        lesson = request.env["op.attendance.sheet"].browse(lesson_id)
        if not lesson.exists():
            return request.render('max_grades_miniapp.max_grades_lesson_students_page', {
                'lesson': lesson,
                'students': [],
                'attend_types': []
            })

        attend_types = request.env["op.attendance.type"].search([])

        students_data = []
        for ln in lesson.attendance_line:
            avatar_data = (ln.student_avatar or ln.student_id.avatar_1920)
            
            avatar_html = Markup('')  # по умолчанию пустой

            # avatar_data может быть bytes, str, bool/False или None
            # Минимальный размер реального изображения - ~1KB (1000 байт)
            # bool (False) - вызовет TypeError при len(), значит требуется try/except
            min_avatar_size = 1000
            valid_avatar = False
            try:
                if avatar_data and isinstance(avatar_data, (bytes, str)) and len(avatar_data) >= min_avatar_size:
                    valid_avatar = True
            except TypeError:
                pass  # avatar_data не поддерживает len() - это bool/False

            if valid_avatar:
                if isinstance(avatar_data, bytes):
                    avatar = 'data:image/png;base64,' + avatar_data.decode('utf-8')
                else:
                    avatar = 'data:image/png;base64,' + avatar_data
                avatar_html = Markup(f'<img src="{avatar}" class="rounded me-2" style="width: 32px; height: 32px; object-fit: cover;"/>')
            else:
                ln_fn = ln.student_id.last_name or ''
                initials = ln_fn[:1].upper() if ln_fn else '?'
                # Разные цвета для разных учеников (хеш от ID)
                colors = ['primary', 'success', 'danger', 'warning', 'info', 'dark']
                color_idx = ln.student_id.id % len(colors)
                color = colors[color_idx]
                avatar_html = Markup(f'<div class="bg-{color} rounded me-2 d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; font-size: 16px; color: white;"><strong>{initials}</strong></div>')

            students_data.append({
                'id': ln.student_id.id,
                'name': f"{ln.student_id.last_name or ''} {ln.student_id.first_name or ''} {ln.student_id.middle_name or ''}".strip(),
                'avatar_html': avatar_html,
            })

        return request.render('max_grades_miniapp.max_grades_lesson_students_page', {
            'lesson': lesson,
            'students': students_data,
            'attend_types': attend_types
        })

    @http.route("/max/grades/api/lessons", type="http", auth="user", methods=["GET"])
    def api_lessons(self, date=None, faculty_id=None):
        """API: Получение списка уроков"""
        user = request.env.user
        date = date or fields.Date.today()

        if user.has_group('base.group_system'):
            if faculty_id:
                faculty = request.env["op.faculty"].browse(int(faculty_id))
                if faculty.exists():
                    domain = [("faculty_id", "=", faculty.id)]
                else:
                    domain = []
            else:
                domain = []
        else:
            faculty = request.env["op.faculty"].search([("partner_id", "=", user.partner_id.id)], limit=1)
            if not faculty:
                return request.make_response(json.dumps({"error": "Вы не прикреплены к преподавателю"}), headers=[('Content-Type', 'application/json')])
            domain = [("faculty_id", "=", faculty.id)]

        try:
            selected_date = fields.Date.from_string(date)
        except Exception:
            selected_date = fields.Date.today()

        domain.append(("attendance_date", "=", selected_date))
        lessons = request.env["op.attendance.sheet"].search(domain)

        return request.make_response(json.dumps({
            "date": date,
            "lessons": [
                {
                    "id": l.id,
                    "subject": l.subject_id.name,
                    "batch": l.batch_id.name,
                    "timing": l.timing or '',
                    "faculty": f"{l.session_id.faculty_id.last_name or ''} {l.session_id.faculty_id.first_name or ''} {l.session_id.faculty_id.middle_name or ''}".strip()
                }
                for l in lessons
            ]
        }), headers=[('Content-Type', 'application/json')])

    @http.route("/max/grades/lesson/<int:lesson_id>/grades", type="http", auth="user", methods=["POST"])
    def save_grades(self, lesson_id):
        """API: Сохранение оценок"""
        body = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else {}
        grades = body.get('grades', [])

        if not grades:
            return request.make_response(json.dumps({"error": "No grades provided"}), headers=[('Content-Type', 'application/json')])

        lesson = request.env["op.attendance.sheet"].browse(lesson_id)
        if not lesson.exists():
            return request.make_response(json.dumps({"error": "Lesson not found"}), headers=[('Content-Type', 'application/json')])

        for g in grades:
            line = request.env["op.attendance.line"].search([
                ("attendance_id", "=", lesson_id),
                ("student_id", "=", g.get("student_id"))
            ], limit=1)
            if line:
                vals = {}
                if g.get("grade_1"): vals["grade_1"] = float(g.get("grade_1"))
                if g.get("grade_2"): vals["grade_2"] = float(g.get("grade_2"))
                if g.get("grade_3"): vals["grade_3"] = float(g.get("grade_3"))
                if g.get("attendance_type_id"): vals["attendance_type_id"] = int(g.get("attendance_type_id"))
                line.write(vals)
        return request.make_response(json.dumps({"success": True}), headers=[('Content-Type', 'application/json')])