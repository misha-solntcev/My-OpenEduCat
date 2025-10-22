# -*- coding: utf-8 -*-
###############################################################################
#
#    Custom Attendance Extension - OpenEduCat
#    Copyright (C) 2025
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api


class UpdateSubjectGrades(models.TransientModel):
    """Расширение мастера обновления оценок по предметам"""
    _inherit = 'update.subject.grades'

    def update_grades(self):
        """
        Расширение метода обновления оценок для обработки тем уроков.
        Вызывается после основного метода обновления.
        """
        # Сначала вызываем оригинальный метод
        result = super(UpdateSubjectGrades, self).update_grades()
        
        # Затем добавляем обработку тем уроков
        subject_grade_obj = self.env['op.subject.grades']
        
        # Получаем все записи посещаемости для обработки тем уроков
        attendance_sheets = self.env['op.attendance.sheet'].search([
            ('attendance_date', '>=', self.start_date),
            ('attendance_date', '<=', self.end_date),
            ('lesson_topic', '!=', False)  # Только записи с указанной темой урока
        ])
        
        # Группируем темы уроков по студентам и предметам
        lesson_topics_data = {}
        for sheet in attendance_sheets:
            register = sheet.register_id
            if not register.subject_id:
                continue
                
            subject_id = register.subject_id.id
            date_str = sheet.attendance_date.strftime('%Y-%m-%d') if sheet.attendance_date else ''
            
            # Для каждой строки посещаемости
            for line in sheet.attendance_line:
                student_id = line.student_id.id
                batch_id = line.batch_id.id if line.batch_id else False
                key = (student_id, subject_id)
                
                if key not in lesson_topics_data:
                    lesson_topics_data[key] = {
                        'topics': [],
                        'batch_id': batch_id
                    }
                    
                # Добавляем тему урока с датой
                lesson_topics_data[key]['topics'].append(f"{date_str}: {sheet.lesson_topic}")
        
        # Обновляем записи предметных оценок
        for (student_id, subject_id), data in lesson_topics_data.items():
            record = subject_grade_obj.search([
                ('student_id', '=', student_id),
                ('subject_id', '=', subject_id),
                ('batch_id', '=', data['batch_id'])
            ], limit=1)
            
            if record:
                record.lesson_topics = '\n'.join(data['topics'])
        
        return result