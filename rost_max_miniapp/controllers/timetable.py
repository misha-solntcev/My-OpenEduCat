# -*- coding: utf-8 -*-
import secrets
import re
import base64
import os
from datetime import timedelta
from odoo import http
from odoo.http import request
from odoo import fields, tools
import logging
from odoo.exceptions import AccessDenied
from .session_middleware import restore_session_if_needed

# Школа работает в Europe/Moscow (UTC+3): тайминги уроков и «сейчас»
# считаем в школьной зоне, а не по UTC сервера / зоне пользователя.
SCHOOL_TZ = 'Europe/Moscow'


def _school_now():
    """Текущий момент naive-datetime в школьной зоне (Europe/Moscow)."""
    return fields.Datetime.context_timestamp(
        request.env.user.with_context(tz=SCHOOL_TZ),
        fields.Datetime.now(),
    ).replace(tzinfo=None)

_logger = logging.getLogger(__name__)

CSRF_SESSION_KEY = 'spa_csrf_token'

TRUSTED_DEVICE_COOKIE = 'td_id'
TRUSTED_DEVICE_AGE = 90 * 86400  # 90 days

MAX_FRAME_HEADERS = {
    'Content-Security-Policy': (
        'frame-ancestors https://*.max.ru https://web.telegram.org '
        'https://telegram.org https://*.telegram.org'
    ),
}


def _spa_response(template, **ctx):
    bundle = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'static', 'src', 'bundle', 'index.js')
    try:
        ctx['bundle_v'] = int(os.path.getmtime(bundle))
    except OSError:
        ctx['bundle_v'] = 0
    response = request.render(template, ctx)
    response.headers.update(MAX_FRAME_HEADERS)
    response.headers['Cache-Control'] = 'no-cache'
    return response


def _get_spa_csrf_token():
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def _check_spa_csrf():
    csrf_token = request.httprequest.headers.get('X-CSRF-Token')
    session_token = request.session.get(CSRF_SESSION_KEY)
    if not session_token or not csrf_token or csrf_token != session_token:
        return request.make_json_response({"error": "CSRF validation failed"}, status=400)
    return None


def _check_trusted_device(user):
    if not user.totp_enabled:
        return True
    key = request.cookies.get(TRUSTED_DEVICE_COOKIE)
    if not key:
        return False
    return request.env['auth_totp.device']._check_credentials_for_uid(
        scope="browser", key=key, uid=user.id
    )


def _generate_trusted_device_cookie(response, user):
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


def _clean_hw_files(files):
    if not isinstance(files, list) or len(files) > 5:
        return None, request.make_json_response(
            {"error": "Не более 5 вложений"}, status=400)
    ALLOWED_MIMES = (
        'image/jpeg', 'image/png', 'image/webp',
        'image/heic', 'image/heif', 'application/pdf',
    )
    MAX_SIZE = 10 * 1024 * 1024
    clean = []
    for f in files:
        if not isinstance(f, dict) or not f.get('b64'):
            continue
        mime = (f.get('mimetype') or '').split(';')[0].strip().lower()
        if mime not in ALLOWED_MIMES:
            return None, request.make_json_response(
                {"error": "Только фото (JPEG/PNG/HEIC) или PDF"},
                status=400)
        try:
            raw = base64.b64decode(f['b64'], validate=True)
        except Exception:
            return None, request.make_json_response(
                {"error": "Некорректный файл"}, status=400)
        if len(raw) > MAX_SIZE:
            return None, request.make_json_response(
                {"error": "Файл больше 10 МБ"}, status=400)
        clean.append({
            'filename': (f.get('filename') or 'attachment')[:128],
            'mimetype': mime,
            'b64': f['b64'],
        })
    return clean, None


class RostMaxTimetableController(http.Controller):
    """Мини-приложение для MAX: расписание занятий"""

    @http.route("/rost_max/login", type="http", auth="public", methods=["GET", "POST"], cors="*", csrf=False)
    def login_page(self, **kw):
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

                request.session.should_rotate = False

                request.session['is_timetable_user'] = True
                user = request.env['res.users'].browse(auth_info['uid'])
                is_admin = user.has_group('base.group_system')

                if user.totp_enabled:
                    if _check_trusted_device(user):
                        pass
                    else:
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
                    "session_id": request.session.sid,
                }

                response = request.make_json_response(response_data)

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

        return _spa_response('rost_max_miniapp.spa_page',
                             csrf_token=_get_spa_csrf_token())

    @http.route("/rost_max/login/totp", type="http", auth="public", methods=["POST"], cors="*", csrf=False)
    def login_totp(self, **kw):
        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response({"error": "Invalid JSON"}, status=400)

        totp_code = body.get('totp_code')
        trusted_device = body.get('trusted_device', False)

        if not totp_code:
            return request.make_json_response(
                {"error": "Код обязателен"}, status=400
            )

        totp_code = re.sub(r'\s', '', totp_code)

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

        request.session.finalize(request.env)
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
            "session_id": request.session.sid,
        }

        response = request.make_json_response(response_data)

        if trusted_device:
            _generate_trusted_device_cookie(response, user)

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
        request.session.pop(CSRF_SESSION_KEY, None)
        request.session.logout()
        return request.redirect('/rost_max/login')

    @http.route("/rost_max/", type="http", auth="public")
    def index(self):
        return _spa_response('rost_max_miniapp.spa_page',
                             csrf_token=_get_spa_csrf_token())

    def _get_user_timetable(self, user, date, faculty_id=None, batch_id=None):
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

        return request.env['op.session'].search(domain, order='start_datetime asc')

    def _faculty_avatar_map(self, sessions):
        avatar_map = {}
        if sessions:
            faculty_ids = sessions.mapped('faculty_id').ids
            with_photo = request.env['op.faculty'].sudo().search(
                [('id', 'in', faculty_ids), ('image_128', '!=', False)])
            avatar_map = {
                f.id: '/web/image/op.faculty/%s/image_512' % f.id
                for f in with_photo
            }
        return avatar_map

    @http.route("/rost_max/api/timetable", type="http", auth="public", methods=["GET"])
    def api_timetable(self, date=None, faculty_id=None, batch_id=None):
        restore_session_if_needed()
        user = request.env.user
        date = date or fields.Date.today()
        date_str = str(date)
        is_admin = user.has_group('base.group_system')

        lessons = self._get_user_timetable(
            user, date, faculty_id=faculty_id, batch_id=batch_id)

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

        avatar_map = self._faculty_avatar_map(lessons) if request.session.uid else {}

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
                    "room": l.classroom_id.sudo().name if l.classroom_id else "",
                    "sheet_id": sheets_map.get(l.id),
                }
                for l in lessons
            ]
        })

    @http.route("/rost_max/api/lesson/<int:lesson_id>/students", type="http", auth="public", methods=["GET"])
    def api_lesson_students(self, lesson_id):
        restore_session_if_needed()
        user = request.env.user
        sheet = request.env['op.attendance.sheet'].sudo().browse(lesson_id)
        if not sheet.exists():
            return request.make_json_response(
                {"lesson": None, "attendance_types": [], "students": []}
            )

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

        avatar_map = {}
        if request.session.uid:
            student_ids = sheet.attendance_line.student_id.ids
            with_photo = request.env['op.student'].sudo().search(
                [('id', 'in', student_ids), ('image_128', '!=', False)])
            avatar_map = {
                s.id: '/web/image/op.student/%s/avatar_1920' % s.id
                for s in with_photo
            }

        attend_types = request.env['op.attendance.type'].search([])
        attendance_types = [{"id": at.id, "name": at.name} for at in attend_types]

        students = []
        for ln in sheet.attendance_line:
            student = ln.student_id
            if not student:
                continue

            avatar = avatar_map.get(student.id, '')

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
                "remark": ln.remark or '',
            })

        lesson = {
            "subject": sheet.subject_id.name if sheet.subject_id else '',
            "can_edit": role in ('admin', 'teacher'),
            "batch": sheet.batch_id.name if sheet.batch_id else '',
            "date": str(sheet.attendance_date) if sheet.attendance_date else '',
            "timing": sheet.timing or '',
            "topic": sheet.lesson_topic or '',
            "homework": getattr(sheet, 'lesson_homework', '') or '',
            "homework_assignment_id": (
                sheet.homework_assignment_id.id
                if getattr(sheet, 'homework_assignment_id', False) else None),
            "homework_answer_required": (
                sheet.homework_assignment_id.answer_required
                if getattr(sheet, 'homework_assignment_id', False)
                else getattr(sheet, 'homework_answer_required', False)),
        }

        u = request.env.user
        columns = {
            "grade_1": True,
            "grade_2": bool(u.miniapp_show_grade_2),
            "grade_3": bool(u.miniapp_show_grade_3),
            "note": bool(u.miniapp_show_note),
            "attendance": True,
        }

        return request.make_json_response({
            "lesson": lesson,
            "attendance_types": attendance_types,
            "students": students,
            "columns": columns,
        })

    @http.route("/rost_max/api/lesson/<int:lesson_id>/save", type="http", auth="public", methods=["POST"], cors="*", csrf=False)
    def api_save_lesson(self, lesson_id, **kw):
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
            if 'attendance_type_id' in row:
                att = row['attendance_type_id']
                vals['attendance_type_id'] = (int(att) if att not in (None, '') else False)
            if 'remark' in row:
                vals['remark'] = (row['remark'] or '').strip() or False

            if vals:
                line.write(vals)
                written += 1

        if sheet.state == 'cancel':
            return request.make_json_response({"success": True, "written": written})

        sheet_vals = {}
        if isinstance(body.get('lesson'), dict):
            lv = body['lesson']
            if 'topic' in lv:
                sheet_vals['lesson_topic'] = (lv['topic'] or '').strip() or False

        if isinstance(body.get('lesson'), dict) and 'homework' in body['lesson'] \
                and hasattr(type(sheet), 'lesson_homework'):
            sheet_vals['lesson_homework'] = (body['lesson']['homework'] or '').strip() or False
        if isinstance(body.get('lesson'), dict) \
                and 'homework_answer_required' in body['lesson'] \
                and hasattr(type(sheet), 'homework_answer_required'):
            flag = bool(body['lesson']['homework_answer_required'])
            sheet_vals['homework_answer_required'] = flag
            if getattr(sheet, 'homework_assignment_id', False):
                sheet.homework_assignment_id.answer_required = flag

        if sheet_vals:
            sheet.write(sheet_vals)

        return request.make_json_response({"success": True, "written": written})

    @http.route("/rost_max/api/lesson/<int:lesson_id>/materials",
                type="http", auth="public", methods=["POST"], cors="*",
                csrf=False)
    def api_lesson_materials(self, lesson_id):
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        sheet = request.env['op.attendance.sheet'].sudo().browse(lesson_id)
        if not sheet.exists():
            return request.make_json_response(
                {"error": "Урок не найден"}, status=404)

        access_err = _check_lesson_write_access(sheet)
        if access_err:
            return access_err
        if sheet.state == 'cancel':
            return request.make_json_response(
                {"error": "Урок отменён — ДЗ недоступно"}, status=403)

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400)

        clean_files, err = _clean_hw_files(body.get('files') or [])
        if err:
            return err
        if not clean_files:
            return request.make_json_response(
                {"error": "Не передано ни одного файла"}, status=400)

        created = False
        if not getattr(sheet, 'homework_assignment_id', False):
            if sheet.state not in ('confirm', 'start', 'done'):
                return request.make_json_response(
                    {"error": "Урок ещё не утверждён — ДЗ недоступно"}, status=409)
            created = True
            hw = (getattr(sheet, 'lesson_homework', '') or '').strip()
            sheet.with_context(
                hw_skip_channel_announce=True,
            ).write({'lesson_homework': hw or 'Домашнее задание (фото)'})
        asg = sheet.homework_assignment_id
        if not asg:
            return request.make_json_response(
                {"error": "Не удалось создать задание — обратитесь к администратору"},
                status=409)
        asg._hw_store_attachments(clean_files)
        if created and hasattr(type(sheet), '_hw_channel_announce'):
            try:
                sheet._hw_channel_announce(
                    asg, 'created', attachments=asg.material_ids)
            except Exception:
                request.env.cr.savepoint()
        return request.make_json_response({
            "success": True,
            "created": created,
            "assignment_id": asg.id,
            "materials": asg._hw_material_payload(),
        })

    @http.route("/rost_max/api/journal/columns", type="http", auth="public", methods=["GET", "POST"], cors="*", csrf=False)
    def api_journal_columns(self, **kw):
        restore_session_if_needed()
        if request.httprequest.method == "POST":
            csrf_err = _check_spa_csrf()
            if csrf_err:
                return csrf_err
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        if request.httprequest.method == "POST":
            try:
                body = request.get_json_data()
            except Exception:
                return request.make_json_response({"error": "Invalid JSON"}, status=400)
            vals = {}
            for key, field in (('grade_2', 'miniapp_show_grade_2'),
                               ('grade_3', 'miniapp_show_grade_3'),
                               ('note', 'miniapp_show_note')):
                if key in body:
                    vals[field] = bool(body[key])
            if vals:
                user.write(vals)

        return request.make_json_response({"columns": {
            "grade_1": True,
            "grade_2": bool(user.miniapp_show_grade_2),
            "grade_3": bool(user.miniapp_show_grade_3),
            "note": bool(user.miniapp_show_note),
            "attendance": True,
        }})

    @http.route("/rost_max/api/user/info", type="http", auth="public", methods=["GET"])
    def api_user_info(self):
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

        avatar = ''
        faculty_rec = request.env['op.faculty'].sudo().search(
            [('partner_id', '=', user.partner_id.id)], limit=1) if is_teacher else None
        student_rec = request.env['op.student'].sudo().search(
            [('partner_id', '=', user.partner_id.id)], limit=1) if is_student else None
        if faculty_rec and faculty_rec.image_128:
            avatar = '/web/image/op.faculty/%s/image_512' % faculty_rec.id
        elif student_rec and student_rec.avatar_128:
            avatar = '/web/image/op.student/%s/avatar_1920' % student_rec.id

        return request.make_json_response({
            "user_name": user.name,
            "avatar": avatar,
            "is_admin": is_admin,
            "is_teacher": is_teacher,
            "is_student": is_student,
            "is_parent": is_parent,
        })

    @http.route("/rost_max/api/dashboard_info", type="http", auth="public", methods=["GET"])
    def api_dashboard_info(self, date=None, **kw):
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)
        student = request.env['op.student'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)

        date_str = date or str(fields.Date.today())
        date_val = fields.Date.from_string(date_str)
        sessions = self._get_user_timetable(user, date_val)

        metrics = {}
        next_lesson = None

        if sessions:
            first_session = sessions[0]
            room = first_session.classroom_id.sudo().name if first_session.classroom_id else None
            next_lesson = {
                "id": first_session.id,
                "subject": first_session.subject_id.name if first_session.subject_id else "Урок",
                "batch": first_session.batch_id.name if first_session.batch_id else "",
                "time": first_session.timing or "12:15 - 13:00",
                "room": room or "Кабинет"
            }

        if is_admin:
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
            all_grades = request.env['op.attendance.line'].sudo().search([
                ('student_id', '=', student.id),
                ('grade_1', '>', 0)
            ]).mapped('grade_1')
            gpa = round(sum(all_grades) / len(all_grades), 2) if all_grades else None
            # Реальный подсчёт незданных ДЗ: опубликованные задания класса,
            # по которым у ученика нет сдачи в состоянии submit/accept.
            batches = student.mapped('active_batch_id')
            pending_asgs = request.env['op.assignment'].sudo().search([
                ('state', '=', 'publish'),
                ('batch_id', 'in', batches.ids),
                ('submission_date', '>=', fields.Datetime.now()),
            ])
            submitted_asg_ids = set(
                request.env['op.assignment.sub.line'].sudo().search([
                    ('assignment_id', 'in', pending_asgs.ids),
                    ('student_id', '=', student.id),
                    ('state', 'in', ['submit', 'accept']),
                ]).mapped('assignment_id').ids
            )
            pending_hw_count = len([a for a in pending_asgs if a.id not in submitted_asg_ids])
            metrics = {
                "gpa": gpa,
                "pending_homework": pending_hw_count,
            }

        return request.make_json_response({
            "is_admin": is_admin,
            "is_teacher": bool(faculty),
            "is_student": bool(student),
            "date": date_str,
            "metrics": metrics,
            "next_lesson": next_lesson,
            **self._dashboard_feed(user, is_admin, faculty, student, sessions, date_val),
        })

    def _dashboard_feed(self, user, is_admin, faculty, student, sessions, date_val):
        now = _school_now()
        role, own_students = _get_user_students(user)
        avatar_map = self._faculty_avatar_map(sessions) if request.session.uid else {}

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
                "faculty_avatar": avatar_map.get(l.faculty_id.id, ''),
                "room": l.classroom_id.sudo().name if l.classroom_id else "",
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
            feed["homework"] = self._student_homework_feed(own_students, now)

        if role in ('teacher', 'admin'):
            if role == 'teacher':
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

            hw_domain = [
                ('state', '=', 'publish'),
                ('submission_date', '>=',
                 fields.Datetime.now() - timedelta(days=7)),
            ]
            if role == 'teacher':
                hw_domain.append(('faculty_id', '=', faculty.id))
            my_asgs = request.env['op.assignment'].sudo().search(
                hw_domain, order='submission_date asc')
            submitted_counts = {
                s['assignment_id'][0]: s['assignment_id_count']
                for s in request.env['op.assignment.sub.line'].sudo().read_group(
                    [('assignment_id', 'in', my_asgs.ids),
                     ('state', 'in', ['submit', 'accept'])],
                    ['assignment_id'], ['assignment_id'])
            }
            to_review_counts = {
                s['assignment_id'][0]: s['assignment_id_count']
                for s in request.env['op.assignment.sub.line'].sudo().read_group(
                    [('assignment_id', 'in', my_asgs.ids),
                     ('state', '=', 'submit')],
                    ['assignment_id'], ['assignment_id'])
            }
            # Принятые (accept) — для прогресса «N из M проверено» в ленте главной.
            accepted_counts = {
                s['assignment_id'][0]: s['assignment_id_count']
                for s in request.env['op.assignment.sub.line'].sudo().read_group(
                    [('assignment_id', 'in', my_asgs.ids),
                     ('state', '=', 'accept')],
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
                # Есть ли что проверять (сдачи в submit — не принятые)
                "to_review": to_review_counts.get(a.id, 0),
                # Принято (accept) — знаменатель прогресса проверки.
                "accepted": accepted_counts.get(a.id, 0),
                "answer_required": a.answer_required,
                "materials_count": len(a._hw_material_payload()),
                "faculty": self._faculty_name(a.faculty_id),
            } for a in my_asgs]

        if role in ('teacher', 'admin'):
            asg_domain = [('state', '=', 'publish')]
            if role == 'teacher':
                asg_domain.append(('faculty_id', '=', faculty.id))
            hw_asgs = request.env['op.assignment'].sudo().search(asg_domain)
            to_review_total = sum(
                s['assignment_id_count']
                for s in request.env['op.assignment.sub.line'].sudo().read_group(
                    [('assignment_id', 'in', hw_asgs.ids),
                     ('state', '=', 'submit')],
                    ['assignment_id'], ['assignment_id']))
            feed["hw_summary"] = {
                "to_review": to_review_total,
                "active": len(hw_asgs),
            }

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

    def _student_homework_feed(self, own_students, now, days_back=7, days_forward=None):
        batches = own_students.mapped('active_batch_id')
        now_server = fields.Datetime.now()
        domain = [
            ('state', '=', 'publish'),
            ('batch_id', 'in', batches.ids),
            ('submission_date', '>=', now_server - timedelta(days=days_back)),
        ]
        if days_forward is not None:
            domain.append(('submission_date', '<=', now_server + timedelta(days=days_forward)))
        asgs = request.env['op.assignment'].sudo().search(
            domain, order='submission_date asc')
        subs = request.env['op.assignment.sub.line'].sudo().search([
            ('assignment_id', 'in', asgs.ids),
            ('student_id', 'in', own_students.ids),
        ])
        sub_map = {s.assignment_id.id: s for s in subs}
        sheets = request.env['op.attendance.sheet'].sudo().search([
            ('homework_assignment_id', 'in', asgs.ids)])
        topic_map = {s.homework_assignment_id.id: s.lesson_topic for s in sheets}
        hw_items = []
        for a in asgs:
            sub = sub_map.get(a.id)
            st = sub.state if sub else 'none'
            hw_items.append({
                "id": a.id,
                "subject": a.subject_id.name if a.subject_id else "",
                "topic": topic_map.get(a.id, ''),
                "issued_at": str(a.grading_assignment_id.issued_date)
                             if a.grading_assignment_id and a.grading_assignment_id.issued_date else "",
                "subject_color": a.subject_id.color if a.subject_id else 0,
                "task": tools.html2plaintext(a.description) or a.name,
                "due": str(a.submission_date) if a.submission_date else "",
                "overdue": bool(a.submission_date and a.submission_date < now_server),
                "answer_required": a.answer_required,
                "state": st,
                "answer": (sub.note or '') if sub else '',
                "mark": (int(sub.marks) if sub and sub.marks else None),
                "teacher_note": (sub.teacher_note or '') if sub else '',
                "submitted_at": str(sub.submission_date) if sub else '',
                "late": bool(sub and a.submission_date
                             and sub.submission_date > a.submission_date),
                "materials": a._hw_material_payload(),
            })
        return hw_items

    @http.route("/rost_max/api/homework", type="http", auth="public", methods=["GET"])
    def api_homework_list(self, **kw):
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        user = request.env.user
        role, own_students = _get_user_students(user)
        if role not in ('student', 'parent') or not own_students:
            return request.make_json_response(
                {"error": "Доступно только ученику и родителю"}, status=403)

        return request.make_json_response({
            "homework": self._student_homework_feed(
                own_students, _school_now(), days_back=30, days_forward=60),
        })

    @staticmethod
    def _batch_short(name):
        return re.sub(r'\s*\d{4}/\d{4}\s*$', '', name or '').strip()

    @staticmethod
    def _faculty_name(f):
        if not f:
            return ""
        return f"{f.last_name or ''} {f.first_name or ''} {f.middle_name or ''}".strip()


    @http.route("/rost_max/api/homework/<int:assignment_id>/submit",
                type="http", auth="public", methods=["POST"], cors="*",
                csrf=False)
    def api_homework_submit(self, assignment_id, **kw):
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        role, own_students = _get_user_students(user)
        if role != 'student' or not own_students:
            return request.make_json_response(
                {"error": "Сдавать может только ученик"}, status=403)
        student = own_students[0]

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400)

        asg = request.env['op.assignment'].sudo().browse(assignment_id)
        if not asg.exists() or asg.state != 'publish':
            return request.make_json_response(
                {"error": "Задание не найдено"}, status=404)

        if student not in asg.allocation_ids:
            return request.make_json_response(
                {"error": "Вам не назначено это задание"}, status=403)

        answer = (body.get('answer') or '').strip()
        if asg.answer_required and not answer:
            return request.make_json_response(
                {"error": "Ответ обязателен"}, status=400)

        clean_files, err = _clean_hw_files(body.get('files') or [])
        if err:
            return err

        sub = request.env['op.assignment.sub.line'].sudo().search([
            ('assignment_id', '=', asg.id),
            ('student_id', '=', student.id),
        ], limit=1)
        vals = {
            'state': 'submit',
            'submission_date': fields.Datetime.now(),
        }
        if answer:
            vals['note'] = answer
        if sub:
            sub.write(vals)
        else:
            sub = request.env['op.assignment.sub.line'].sudo().create(dict(
                vals, assignment_id=asg.id, student_id=student.id))
        if clean_files:
            sub._hw_store_attachments(clean_files)

        return request.make_json_response({"success": True})

    @http.route("/rost_max/api/homework/<int:assignment_id>/materials",
                type="http", auth="public", methods=["GET"])
    def api_homework_materials(self, assignment_id):
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        asg = request.env['op.assignment'].sudo().browse(assignment_id)
        if not asg.exists():
            return request.make_json_response(
                {"error": "Задание не найдено"}, status=404)

        is_admin = user.has_group('base.group_system')
        role, own_students = _get_user_students(user)
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)
        allowed = is_admin or (faculty and asg.faculty_id == faculty) or (
            role in ('student', 'parent') and own_students
            and own_students & asg.allocation_ids)
        if not allowed:
            return request.make_json_response(
                {"error": "Нет доступа к заданию"}, status=403)

        return request.make_json_response({
            "materials": asg._hw_material_payload(),
        })

    @http.route("/rost_max/api/homework/<int:assignment_id>/materials",
                type="http", auth="public", methods=["POST"], cors="*",
                csrf=False)
    def api_homework_materials_set(self, assignment_id):
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)

        asg = request.env['op.assignment'].sudo().browse(assignment_id)
        if not asg.exists():
            return request.make_json_response(
                {"error": "Задание не найдено"}, status=404)
        if not is_admin and (not faculty or asg.faculty_id != faculty):
            return request.make_json_response(
                {"error": "Доступно только автору задания"}, status=403)

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400)

        clean_files, err = _clean_hw_files(body.get('files') or [])
        if err:
            return err
        asg._hw_store_attachments(clean_files)
        return request.make_json_response({
            "success": True,
            "materials": asg._hw_material_payload(),
        })

    @http.route("/rost_max/api/homework/<int:assignment_id>/submissions",
                type="http", auth="public", methods=["GET"])
    def api_homework_submissions(self, assignment_id, **kw):
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)

        asg = request.env['op.assignment'].sudo().browse(assignment_id)
        if not asg.exists():
            return request.make_json_response(
                {"error": "Задание не найдено"}, status=404)
        if not is_admin and (not faculty or asg.faculty_id != faculty):
            return request.make_json_response(
                {"error": "Доступно только автору задания"}, status=403)

        students = []
        for st in asg.allocation_ids:
            sub = request.env['op.assignment.sub.line'].sudo().search([
                ('assignment_id', '=', asg.id),
                ('student_id', '=', st.id),
            ], limit=1)
            attachments = []
            if sub:
                atts = request.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'op.assignment.sub.line'),
                    ('res_id', '=', sub.id),
                    ('res_field', '=', 'hw_attachment'),
                ], order='id asc')
                for att in atts:
                    token = request.env['hw.attachment.token'].sudo().create({
                        'attachment_id': att.id,
                    })
                    attachments.append({
                        'name': att.name or 'attachment',
                        'mimetype': att.mimetype or '',
                        'url': '/rost_max/hw_att/%s' % token.token,
                    })
            name = ("%s %s" % (
                st.last_name or '', st.first_name or '')).strip()
            avatar = ('/web/image/op.student/%s/avatar_1920' % st.id) if st.image_128 else ''
            students.append({
                "avatar": avatar,
                "sub_id": sub.id if sub else None,
                "student_id": st.id,
                "name": name,
                "state": sub.state if sub else 'none',
                "answer": (sub.note or '') if sub else '',
                "mark": (int(sub.marks) if sub and sub.marks else None),
                "submitted_at": str(sub.submission_date) if sub else '',
                "late": bool(sub and asg.submission_date
                             and sub.submission_date > asg.submission_date),
                "teacher_note": (sub.teacher_note or '') if sub else '',
                "attachments": attachments,
            })
        students.sort(key=lambda s: (
            s['state'] == 'none', s['name']))
        sub_ids = [s['sub_id'] for s in students if s['sub_id']]
        messages = request.env['mail.message'].sudo().search_read(
            [('model', '=', 'op.assignment.sub.line'),
             ('res_id', 'in', sub_ids)],
            fields=['res_id', 'date'], order='date asc')
        tracking = request.env['mail.tracking.value'].sudo().search_read(
            [('mail_message_id', 'in', [m['id'] for m in messages])],
            fields=['mail_message_id', 'field_id', 'old_value_char',
                    'new_value_char'])
        field_ids = list({t['field_id'][0] for t in tracking if t['field_id']})
        field_names = {
            f['id']: f['name']
            for f in request.env['ir.model.fields'].sudo().browse(field_ids)
        } if field_ids else {}
        track_by_msg = {}
        for t in tracking:
            fname = field_names.get(t['field_id'][0]) if t['field_id'] else None
            if fname == 'state':
                track_by_msg.setdefault(t['mail_message_id'][0], []).append(t)
        for s in students:
            history = []
            if s['sub_id']:
                for m in messages:
                    if m['res_id'] != s['sub_id']:
                        continue
                    for t in track_by_msg.get(m['id'], []):
                        new_label = t['new_value_char']
                        if not history or history[-1]['label'] != new_label:
                            history.append({
                                'date': str(m['date'])[:10],
                                'label': new_label,
                            })
                        break
            s['history'] = history
        return request.make_json_response({
            "assignment": {
                "id": asg.id,
                "subject": asg.subject_id.name or '',
                "task": tools.html2plaintext(asg.description) or asg.name,
                "due": str(asg.submission_date) if asg.submission_date else '',
                "answer_required": asg.answer_required,
            },
            "students": students,
        })

    @http.route("/rost_max/api/homework/submission/<int:sub_id>/review",
                type="http", auth="public", methods=["POST"], cors="*",
                csrf=False)
    def api_homework_review(self, sub_id, **kw):
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)

        sub = request.env['op.assignment.sub.line'].sudo().browse(sub_id)
        if not sub.exists():
            return request.make_json_response(
                {"error": "Сдача не найдена"}, status=404)
        if not is_admin and (not faculty
                             or sub.assignment_id.faculty_id != faculty):
            return request.make_json_response(
                {"error": "Доступно только автору задания"}, status=403)

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400)
        action = body.get('action')
        if action not in ('accept', 'change'):
            return request.make_json_response(
                {"error": "action должен быть accept|change"}, status=400)

        vals = {'state': 'accept' if action == 'accept' else 'change'}
        if 'teacher_note' in body:
            vals['teacher_note'] = (body.get('teacher_note') or '').strip()
        if 'mark' in body:
            mark = body.get('mark')
            if mark is None or mark == '':
                vals['marks'] = 0.0
            else:
                try:
                    mark = float(mark)
                except (TypeError, ValueError):
                    return request.make_json_response(
                        {"error": "Оценка должна быть числом"}, status=400)
                if mark not in (2, 3, 4, 5):
                    return request.make_json_response(
                        {"error": "Оценка должна быть 2, 3, 4 или 5"}, status=400)
                vals['marks'] = mark
        sub.write(vals)
        return request.make_json_response({"success": True})

    @http.route("/rost_max/api/teacher_homework", type="http",
                auth="public", methods=["GET"])
    def api_teacher_homework(self, **kw):
        restore_session_if_needed()
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)
        if not is_admin and not faculty:
            return request.make_json_response(
                {"error": "Доступно только учителю и админу"}, status=403)

        domain = [('state', 'in', ('publish', 'finish'))]
        if not is_admin:
            domain.append(('faculty_id', '=', faculty.id))
        asgs = request.env['op.assignment'].sudo().search(
            domain, order='submission_date asc')

        submitted_counts = {
            s['assignment_id'][0]: s['assignment_id_count']
            for s in request.env['op.assignment.sub.line'].sudo().read_group(
                [('assignment_id', 'in', asgs.ids),
                 ('state', 'in', ['submit', 'accept'])],
                ['assignment_id'], ['assignment_id'])
        }
        to_review_counts = {
            s['assignment_id'][0]: s['assignment_id_count']
            for s in request.env['op.assignment.sub.line'].sudo().read_group(
                [('assignment_id', 'in', asgs.ids),
                 ('state', '=', 'submit')],
                ['assignment_id'], ['assignment_id'])
        }
        accepted_counts = {
            s['assignment_id'][0]: s['assignment_id_count']
            for s in request.env['op.assignment.sub.line'].sudo().read_group(
                [('assignment_id', 'in', asgs.ids),
                 ('state', '=', 'accept')],
                ['assignment_id'], ['assignment_id'])
        }
        now = fields.Datetime.now()
        hw_sheets = request.env['op.attendance.sheet'].sudo().search([
            ('homework_assignment_id', 'in', asgs.ids)])
        topic_map = {s.homework_assignment_id.id: s.lesson_topic
                     for s in hw_sheets}
        return request.make_json_response({"homework": [{
            "id": a.id,
            "state": a.state,
            "subject": a.subject_id.name if a.subject_id else "",
            "subject_color": a.subject_id.color if a.subject_id else 0,
            "topic": topic_map.get(a.id, ''),
            "issued_at": str(a.grading_assignment_id.issued_date)
                         if a.grading_assignment_id and a.grading_assignment_id.issued_date else "",
            "batch": self._batch_short(a.batch_id.name) if a.batch_id else "",
            "task": tools.html2plaintext(a.description) or a.name,
            "due": str(a.submission_date) if a.submission_date else "",
            "overdue": bool(a.state == 'publish' and a.submission_date
                            and a.submission_date < now),
            "submitted": submitted_counts.get(a.id, 0),
            "total": len(a.allocation_ids),
            "to_review": to_review_counts.get(a.id, 0),
            "accepted": accepted_counts.get(a.id, 0),
            "answer_required": a.answer_required,
            "materials_count": len(a._hw_material_payload()),
            "sheet_id": request.env['op.attendance.sheet'].sudo().search([
                ('homework_assignment_id', '=', a.id)], limit=1).id or None,
            "faculty": self._faculty_name(a.faculty_id),
        } for a in asgs]})

    @http.route("/rost_max/api/homework/<int:assignment_id>/edit",
                type="http", auth="public", methods=["POST"], cors="*",
                csrf=False)
    def api_homework_edit(self, assignment_id, **kw):
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)

        asg = request.env['op.assignment'].sudo().browse(assignment_id)
        if not asg.exists():
            return request.make_json_response(
                {"error": "Задание не найдено"}, status=404)
        if not is_admin and (not faculty or asg.faculty_id != faculty):
            return request.make_json_response(
                {"error": "Доступно только автору задания"}, status=403)
        if asg.state not in ('publish', 'finish'):
            return request.make_json_response(
                {"error": "Задание отменено — правка недоступна"}, status=409)

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400)

        sheet_vals = {}
        assignment_vals = {}
        if 'topic' in body:
            topic = (body.get('topic') or '').strip()
            sheet = request.env['op.attendance.sheet'].sudo().search([
                ('homework_assignment_id', '=', assignment_id)], limit=1)
            if not sheet:
                return request.make_json_response(
                    {"error": "Задание создано вне журнала урока — "
                              "тема правится только в ПК-форме журнала"},
                    status=409)
            if sheet.state not in ('confirm', 'start', 'done'):
                return request.make_json_response(
                    {"error": "Журнал урока не активен — правка недоступна"},
                    status=409)
            sheet_vals['lesson_topic'] = topic

        if 'task' in body:
            task = (body.get('task') or '').strip()
            if not task:
                return request.make_json_response(
                    {"error": "Текст задания не может быть пустым"},
                    status=400)
            sheet = request.env['op.attendance.sheet'].sudo().search([
                ('homework_assignment_id', '=', assignment_id)], limit=1)
            if not sheet:
                return request.make_json_response(
                    {"error": "Задание создано вне журнала урока — "
                              "текст правится только в ПК-форме задания"},
                    status=409)
            if sheet.state not in ('confirm', 'start', 'done'):
                return request.make_json_response(
                    {"error": "Журнал урока не активен — правка недоступна"},
                    status=409)
            sheet_vals['lesson_homework'] = task

        if 'due' in body:
            due_raw = (body.get('due') or '').strip()
            if not due_raw:
                return request.make_json_response(
                    {"error": "Срок обязателен"}, status=400)
            try:
                due_dt = fields.Datetime.from_string(due_raw)
            except ValueError:
                return request.make_json_response(
                    {"error": "Некорректный формат срока"}, status=400)
            if due_dt < asg.issued_date:
                return request.make_json_response(
                    {"error": "Срок не может быть раньше даты выдачи"},
                    status=400)
            assignment_vals['submission_date'] = due_dt

        if 'answer_required' in body:
            assignment_vals['answer_required'] = bool(body.get('answer_required'))

        if assignment_vals:
            asg.write(assignment_vals)
        if sheet_vals:
            sheet.write(sheet_vals)

        return request.make_json_response({"success": True})

    @http.route("/rost_max/api/homework/<int:assignment_id>/finish",
                type="http", auth="public", methods=["POST"], cors="*",
                csrf=False)
    def api_homework_finish(self, assignment_id, **kw):
        restore_session_if_needed()
        csrf_err = _check_spa_csrf()
        if csrf_err:
            return csrf_err
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401)

        user = request.env.user
        is_admin = user.has_group('base.group_system')
        faculty = request.env['op.faculty'].sudo().search([
            ('partner_id', '=', user.partner_id.id)], limit=1)

        asg = request.env['op.assignment'].sudo().browse(assignment_id)
        if not asg.exists():
            return request.make_json_response(
                {"error": "Задание не найдено"}, status=404)
        if not is_admin and (not faculty or asg.faculty_id != faculty):
            return request.make_json_response(
                {"error": "Доступно только автору задания"}, status=403)

        try:
            body = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400)
        action = body.get('action')
        if action == 'finish':
            if asg.state != 'publish':
                return request.make_json_response(
                    {"error": "Завершить можно только активное задание"},
                    status=409)
            asg.act_finish()
        elif action == 'resume':
            if asg.state != 'finish':
                return request.make_json_response(
                    {"error": "Возобновить можно только завершённое задание"},
                    status=409)
            asg.act_set_to_draft()
            asg.act_publish()
        else:
            return request.make_json_response(
                {"error": "action должен быть finish|resume"}, status=400)
        return request.make_json_response({"success": True})

    @http.route("/rost_max/hw_att/<string:token>", type="http",
                methods=["GET"], readonly=True)
    def hw_attachment_download(self, token):
        att = request.env['hw.attachment.token'].sudo().get_valid(token)
        if not att:
            return request.make_response(
                'Ссылка устарела. Откройте сдачу заново.',
                status=410,
                headers=[('Content-Type', 'text/plain; charset=utf-8')])
        stream = request.env['ir.binary']._get_stream_from(
            att, 'raw', att.name, 'name', att.mimetype)
        return stream.get_response(as_attachment=True)

    @http.route("/rost_max/api/faculties", type="http", auth="public", methods=["GET"])
    def api_faculties(self):
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
        restore_session_if_needed()
        user = request.env.user
        if not user.has_group('base.group_system'):
            return request.make_json_response({"batches": []})

        today = fields.Date.today()
        year = request.env['op.academic.year'].sudo().search([
            ('start_date', '<=', today), ('end_date', '>=', today)
        ], limit=1)
        domain = []
        if year:
            domain.append(('end_date', '>=', year.start_date))
            domain.append(('start_date', '<=', year.end_date))

        batches = request.env['op.batch'].search(domain, order='sequence, name')
        year_re = re.compile(r'\s*\d{4}[/\-\u2013]\d{4}\s*')
        return request.make_json_response({
            "batches": [
                {"id": b.id, "name": year_re.sub(' ', b.name).strip()}
                for b in batches
            ]
        })

    def _get_quarter_terms(self):
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
        today = fields.Date.today()
        for i in sorted(q_map):
            term = q_map[i]
            if term.term_start_date <= today <= term.term_end_date:
                return i
        started = [i for i in sorted(q_map) if q_map[i].term_start_date <= today]
        return started[-1] if started else 1

    @staticmethod
    def _line_payload(ln):
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
