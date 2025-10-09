###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
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


class OpUpdateSubjectGrades(models.TransientModel):
    _name = "op.update.subject.grades"
    _description = "Update Subject Grades"

    def update_subject_grades(self):
        # Получаем все записи посещаемости с оценками или поведением
        attendance_lines = self.env['op.attendance.line'].search(['|', ('x_mark', '!=', False), ('x_behavior', '!=', False)])
        
        # Группируем данные по студенту и предмету
        grades_data = {}
        for line in attendance_lines:
            # Используем x_subject вместо course_id
            if line.student_id and line.x_subject:
                key = (line.student_id.id, line.x_subject.id)
                if key not in grades_data:
                    grades_data[key] = {
                        'student_id': line.student_id.id,
                        'subject_id': line.x_subject.id,
                        'batch_id': line.batch_id.id if line.batch_id else False,
                        'entries': [],  # Список записей с датами, оценками и поведением
                        'total_classes': 0,
                        'present_classes': 0,
                        'last_attendance_date': line.attendance_date,
                    }
                
                # Создаем запись с датой, оценкой и поведением
                entry = {
                    'date': line.attendance_date.strftime('%Y-%m-%d') if line.attendance_date else '',
                    'mark': line.x_mark or '',
                    'behavior': line.x_behavior or ''
                }
                grades_data[key]['entries'].append(entry)
                
                # Увеличиваем счетчики
                grades_data[key]['total_classes'] += 1
                if line.present:
                    grades_data[key]['present_classes'] += 1
                # Обновляем дату последнего занятия
                if line.attendance_date and (not grades_data[key]['last_attendance_date'] or 
                                             line.attendance_date > grades_data[key]['last_attendance_date']):
                    grades_data[key]['last_attendance_date'] = line.attendance_date
        
        # Находим существующие записи в op.subject.grades для соответствующих студентов и предметов
        existing_records = self.env['op.subject.grades'].search([
            ('student_id', 'in', [data['student_id'] for data in grades_data.values()]),
            ('subject_id', 'in', [data['subject_id'] for data in grades_data.values()])
        ])
        
        # Создаем словарь для быстрого поиска существующих записей
        existing_map = {}
        for record in existing_records:
            key = (record.student_id.id, record.subject_id.id)
            existing_map[key] = record
        
        # Обновляем существующие или создаем новые записи
        updated_count = 0
        created_count = 0

        for key, data in grades_data.items():
            if key in existing_map:
                # Обновляем существующую запись
                record = existing_map[key]
                
                # Вычисляем среднюю оценку из всех числовых значений (x_mark и x_behavior)
                all_numeric_marks = []
                
                # Собираем все оценки и поведения из записей
                all_marks = []
                all_behaviors = []
                all_dates = []
                
                # Для отображения в таблице будем использовать формат: дата|оценка|поведение
                table_entries = []
                
                for entry in data['entries']:
                    # Добавляем запись для таблицы
                    table_entry = "{}|{}|{}".format(
                        entry['date'] or '',
                        entry['mark'] or '',
                        entry['behavior'] or ''
                    )
                    table_entries.append(table_entry)
                    
                    if entry['date']:
                        all_dates.append(entry['date'])
                
                # Вычисляем среднюю оценку
                if all_numeric_marks:
                    average_mark = sum(all_numeric_marks) / len(all_numeric_marks)
                else:
                    average_mark = 0.0
                
                # Преобразуем списки в строки
                marks_str = ', '.join(str(mark).strip() for mark in all_marks) if all_marks else ''
                behaviors_str = ', '.join(str(behavior).strip() for behavior in all_behaviors) if all_behaviors else ''
                attendance_dates_str = ', '.join(str(date).strip() for date in all_dates) if all_dates else ''
                table_entries_str = ', '.join(table_entries) if table_entries else ''
                table_entries_str = ', '.join(table_entries) if table_entries else ''
                
                # Обновляем запись
                record.write({
                    'batch_id': data['batch_id'],
                    'marks': marks_str,
                    'behaviors': behaviors_str,
                    'attendance_dates': attendance_dates_str,
                    'average_mark': average_mark,
                    'table_entries': table_entries_str,  # Добавляем новое поле для таблицы
                    'total_classes': data['total_classes'],
                    'present_classes': data['present_classes'],
                    'last_attendance_date': data['last_attendance_date'],
                })
                updated_count += 1
            else:
                # Создаем новую запись
                # Вычисляем среднюю оценку из всех числовых значений (x_mark и x_behavior)
                all_numeric_marks = []
                
                # Собираем все оценки и поведения из записей
                all_marks = []
                all_behaviors = []
                all_dates = []
                
                # Для отображения в таблице будем использовать формат: дата|оценка|поведение
                table_entries = []
                
                for entry in data['entries']:
                    # Добавляем запись для таблицы
                    table_entry = "{}|{}|{}".format(
                        entry['date'] or '',
                        entry['mark'] or '',
                        entry['behavior'] or ''
                    )
                    table_entries.append(table_entry)
                    
                    if entry['date']:
                        all_dates.append(entry['date'])
                
                # Вычисляем среднюю оценку
                if all_numeric_marks:
                    average_mark = sum(all_numeric_marks) / len(all_numeric_marks)
                else:
                    average_mark = 0.0
                
                # Преобразуем списки в строки
                marks_str = ', '.join(str(mark).strip() for mark in all_marks) if all_marks else ''
                behaviors_str = ', '.join(str(behavior).strip() for behavior in all_behaviors) if all_behaviors else ''
                attendance_dates_str = ', '.join(str(date).strip() for date in all_dates) if all_dates else ''
                
                # Создаем запись
                self.env['op.subject.grades'].create({
                    'student_id': data['student_id'],
                    'subject_id': data['subject_id'],
                    'batch_id': data['batch_id'],
                    'marks': marks_str,
                    'behaviors': behaviors_str,
                    'attendance_dates': attendance_dates_str,
                    'average_mark': average_mark,
                    'table_entries': table_entries_str,  # Добавляем новое поле для таблицы
                    'total_classes': data['total_classes'],
                    'present_classes': data['present_classes'],
                    'last_attendance_date': data['last_attendance_date'],
                })
                created_count += 1

        # Удаляем записи, которые больше не соответствуют ни одной паре студент-предмет
        # Находим все пары студент-предмет в новых данных
        current_pairs = set(grades_data.keys())
        
        # Находим существующие пары в базе
        all_existing_records = self.env['op.subject.grades'].search([])
        existing_pairs = set()
        for record in all_existing_records:
            key = (record.student_id.id, record.subject_id.id)
            existing_pairs.add(key)
        
        # Удаляем те, которых нет в новых данных
        pairs_to_delete = existing_pairs - current_pairs
        for key in pairs_to_delete:
            if key in existing_map:
                existing_map[key].unlink()

        # Display notification that auto-dismisses after a few seconds and then closes the wizard
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Subject grades have been updated successfully. {updated_count} records updated, {created_count} records created.',
                'sticky': False,  # Non-sticky notification that auto-dismisses
                'type': 'success',
                'next': {  # This will close the wizard after showing the notification
                    'type': 'ir.actions.act_window_close'
                }
            }
        }