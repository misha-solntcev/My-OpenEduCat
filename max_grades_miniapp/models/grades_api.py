# -*- coding: utf-8 -*-
"""
Утилиты для работы с оценками в mini-app.
Вынесена логика из контроллеров для лучшей структуры и переиспользования.
"""
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class GradesUtils:
    """Утилитарный класс для работы с оценками (не модель Odoo)"""
    
    @classmethod
    def get_lessons(cls, env, date=None, faculty_id=None, user_id=None):
        """
        Получение списка уроков для преподавателя.
        Args:
            env: Odoo environment
            date: Дата в формате YYYY-MM-DD
            faculty_id: ID преподавателя (op.faculty)
            user_id: ID пользователя (res.users)
        Returns:
            Список словарей с данными уроков
        """
        AttendanceSheet = env['op.attendance.sheet']
        Faculty = env['op.faculty']

        # Определяем фильтр по преподавателю
        if user_id:
            user = env['res.users'].browse(user_id)
            faculty = Faculty.search([('partner_id', '=', user.partner_id.id)], limit=1)
            if faculty:
                domain = [('faculty_id', '=', faculty.id)]
            else:
                return []
        elif faculty_id:
            domain = [('faculty_id', '=', faculty_id)]
        else:
            domain = []

        # Добавляем фильтр по дате
        try:
            selected_date = fields.Date.from_string(date) if date else fields.Date.today()
            domain.append(('attendance_date', '=', selected_date))
        except Exception:
            domain.append(('attendance_date', '=', fields.Date.today()))

        lessons = AttendanceSheet.search(domain)
        return [
            {
                'id': l.id,
                'subject': l.subject_id.name,
                'batch': l.batch_id.name,
                'timing': l.timing or ''
            }
            for l in lessons
        ]

    @classmethod
    def save_grades(cls, env, lesson_id, grades_data):
        """
        Сохранение оценок для урока.
        Args:
            env: Odoo environment
            lesson_id: ID урока (op.attendance.sheet)
            grades_data: Список словарей с данными оценок
        Returns:
            True при успехе, False при ошибке
        """
        AttendanceLine = env['op.attendance.line']
        lesson = env['op.attendance.sheet'].browse(lesson_id)
        if not lesson.exists():
            return False

        # Получаем все строки посещаемости для урока одним запросом
        student_ids = [g.get('student_id') for g in grades_data]
        lines = AttendanceLine.search([
            ('attendance_id', '=', lesson_id),
            ('student_id', 'in', student_ids)
        ])

        # Сопоставляем строки с данными
        line_by_student = {line.student_id.id: line for line in lines}

        for g in grades_data:
            student_id = g.get('student_id')
            line = line_by_student.get(student_id)
            if line:
                vals = {}
                if g.get('grade_1'):
                    vals['grade_1'] = float(g.get('grade_1'))
                if g.get('grade_2'):
                    vals['grade_2'] = float(g.get('grade_2'))
                if g.get('grade_3'):
                    vals['grade_3'] = float(g.get('grade_3'))
                if g.get('attendance_type_id'):
                    vals['attendance_type_id'] = int(g.get('attendance_type_id'))
                line.write(vals)

        return True

    @classmethod
    def get_lesson_students(cls, env, lesson_id):
        """
        Получение данных студентов для урока.
        Args:
            env: Odoo environment
            lesson_id: ID урока (op.attendance.sheet)
        Returns:
            Список словарей с данными студентов
        """
        lesson = env['op.attendance.sheet'].browse(lesson_id)
        if not lesson.exists():
            return []

        attend_types = env['op.attendance.type'].search([])
        students_data = []

        for ln in lesson.attendance_line:
            # Аватар
            avatar_data = ln.student_avatar or ln.student_id.avatar_1920
            avatar = ''
            if avatar_data and isinstance(avatar_data, bytes) and len(avatar_data) > 0:
                data = avatar_data.decode()
                mime = 'svg+xml' if data.startswith('PD94bWwg') else 'png'
                avatar = f'data:image/{mime};base64,{data}'

            # Инициалы
            ln_fn = ln.student_id.last_name or ''
            ln_ln = ln.student_id.first_name or ''
            initials = f"{ln_fn[:1]}{ln_ln[:1]}".upper() if ln_fn or ln_ln else '?'

            students_data.append({
                'id': ln.student_id.id,
                'name': f"{ln.student_id.last_name or ''} {ln.student_id.first_name or ''}".strip(),
                'avatar': avatar,
                'initials': initials,
                'grade_1': ln.grade_1,
                'grade_2': ln.grade_2,
                'grade_3': ln.grade_3,
                'attendance_type_id': ln.attendance_type_id.id,
                'attendance_types': [
                    {'id': at.id, 'name': at.name, 'selected': ln.attendance_type_id.id == at.id}
                    for at in attend_types
                ]
            })

        return students_data
