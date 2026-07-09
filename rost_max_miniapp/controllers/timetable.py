# -*- coding: utf-8 -*-
import json
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
                body = json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                return request.make_response(
                    json.dumps({"error": "Invalid JSON"}),
                    headers=[('Content-Type', 'application/json')]
                )

            email = body.get('email')
            password = body.get('password')

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
                request.session['is_timetable_user'] = True
                user = request.env['res.users'].browse(auth_info['uid'])
                is_admin = user.has_group('base.group_system')
                return request.make_response(
                    json.dumps({"success": True, "user_name": user.name, "is_admin": is_admin}),
                    headers=[('Content-Type', 'application/json')]
                )
            except Exception:
                return request.make_response(
                    json.dumps({"error": "Ошибка аутентификации"}),
                    headers=[('Content-Type', 'application/json')]
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

        return request.make_response(json.dumps({
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
        }), headers=[('Content-Type', 'application/json')])

    @http.route("/rost_max/api/lesson/<int:lesson_id>/students", type="http", auth="public", methods=["GET"])
    def api_lesson_students(self, lesson_id):
        """API: список учеников по уроку с оценками"""
        sheet = request.env['op.attendance.sheet'].browse(lesson_id)
        if not sheet.exists():
            return request.make_response(json.dumps({"students": []}), headers=[('Content-Type', 'application/json')])
        
        students = request.env['op.student'].search([], order='last_name,first_name')
        return request.make_response(json.dumps({
            "lesson_id": lesson_id,
            "students": [
                {
                    "id": s.id,
                    "name": f"{s.last_name or ''} {s.first_name or ''}".strip()
                }
                for s in students
            ]
        }), headers=[('Content-Type', 'application/json')])

    @http.route("/rost_max/api/set_grade", type="http", auth="public", methods=["POST"], cors="*", csrf=False)
    def api_set_grade(self, **kw):
        """API: выставление оценки"""
        try:
            body = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            return request.make_response(json.dumps({"error": "Invalid JSON"}), headers=[('Content-Type', 'application/json')])
        
        return request.make_response(json.dumps({"success": True}), headers=[('Content-Type', 'application/json')])

    @http.route("/rost_max/api/faculties", type="http", auth="public", methods=["GET"])
    def api_faculties(self):
        """API: список учителей (только для админа)"""
        user = request.env.user
        if not user.has_group('base.group_system'):
            return request.make_response(json.dumps({"faculties": []}), headers=[('Content-Type', 'application/json')])

        faculties = request.env['op.faculty'].search([], order='last_name,first_name')
        return request.make_response(json.dumps({
            "faculties": [
                {
                    "id": f.id,
                    "name": f"{f.last_name or ''} {f.first_name or ''} {f.middle_name or ''}".strip()
                }
                for f in faculties
            ]
        }), headers=[('Content-Type', 'application/json')])