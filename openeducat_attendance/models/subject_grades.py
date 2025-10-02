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

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    student_id = fields.Many2one('op.student', 'Student', required=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    marks = fields.Text('All Marks (x_mark)')
    behaviors = fields.Text('All Behaviors (x_behavior)')
    average_mark = fields.Float('Average Mark', digits=(3, 2))
    last_attendance_date = fields.Date('Last Attendance Date')
    total_classes = fields.Integer('Total Classes')
    present_classes = fields.Integer('Present Classes')
    textbook_image = fields.Binary('Textbook Image', compute='_compute_textbook_image')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # Получаем группы
        student_group = self.env.ref('__custom__.group_op_students', raise_if_not_found=False)
        faculty_group = self.env.ref('__custom__.group_op_faculty', raise_if_not_found=False)
        attendance_manager_group = self.env.ref('openeducat_attendance.group_op_attendance_manager', raise_if_not_found=False)
        
        # Проверим, принадлежит ли текущий пользователь группам
        is_student = student_group in self.env.user.groups_id if student_group else False
        is_faculty = faculty_group in self.env.user.groups_id if faculty_group else False
        is_attendance_manager = attendance_manager_group in self.env.user.groups_id if attendance_manager_group else False
        
        # Для студентов всегда применяем фильтрацию, независимо от существующих фильтров
        if is_student:
            # Пользователь в группе студентов, проверим, связан ли он со студентом
            student_record = self.env['op.student'].search([('user_id', '=', self.env.user.id)], limit=1)
            # Проверяем, что запись существует и не пустая
            if student_record and student_record.id:
                # Добавляем или заменяем условие фильтрации по студенту
                student_id = student_record.id
                # Удаляем существующий фильтр по student_id, если он есть
                args = [arg for arg in args if not (isinstance(arg, (list, tuple)) and len(arg) >= 3 and arg[0] == 'student_id' and arg[1] == '=')]
                # Добавляем новый фильтр по student_id
                args += [('student_id', '=', student_id)]
            else:
                # Пользователь в группе студентов, но не связан со студентом (преподаватель)
                # В этом случае не применяем фильтрацию, показываем все записи
                pass
        elif is_faculty:
            # Пользователь в группе преподавателей
            # Не применяем фильтрацию, показываем все записи
            pass
        else:
            # Пользователь не в группе студентов и не в группе преподавателей (администратор, менеджер и т.д.)
            # Не применяем фильтрацию, показываем все записи
            pass
        
        # Вызываем родительский метод в зависимости от значения count
        if count:
            result = super(OpSubjectGrades, self).search_count(args)
        else:
            result = super(OpSubjectGrades, self)._search(args, offset=offset, limit=limit, order=order)
        
        return result

    def read(self, fields=None, load='_classic_read'):
        # Получаем группы
        student_group = self.env.ref('__custom__.group_op_students', raise_if_not_found=False)
        faculty_group = self.env.ref('__custom__.group_op_faculty', raise_if_not_found=False)
        attendance_manager_group = self.env.ref('openeducat_attendance.group_op_attendance_manager', raise_if_not_found=False)
        
        # Проверим, принадлежит ли текущий пользователь группам
        is_student = student_group in self.env.user.groups_id if student_group else False
        is_faculty = faculty_group in self.env.user.groups_id if faculty_group else False
        is_attendance_manager = attendance_manager_group in self.env.user.groups_id if attendance_manager_group else False
        
        # Для студентов проверяем, что все записи принадлежат им
        if is_student:
            # Пользователь в группе студентов, проверим, связан ли он со студентом
            student_record = self.env['op.student'].search([('user_id', '=', self.env.user.id)], limit=1)
            # Проверяем, что запись существует и не пустая
            if student_record and student_record.id:
                # Проверяем, что все записи принадлежат текущему студенту
                record_ids = []
                for record in self:
                    if record.student_id.id == student_record.id:
                        record_ids.append(record.id)
                
                # Если какие-то записи не принадлежат текущему студенту, фильтруем их
                if len(record_ids) != len(self):
                    # Ограничиваем доступ только к тем записям, которые принадлежат студенту
                    filtered_records = self.browse(record_ids)
                    return super(OpSubjectGrades, filtered_records).read(fields, load)
            else:
                # Пользователь в группе студентов, но не связан со студентом (преподаватель)
                # В этом случае разрешаем чтение
                pass
        elif is_faculty:
            # Пользователь в группе преподавателей
            # Разрешаем чтение
            pass
        else:
            # Пользователь не в группе студентов и не в группе преподавателей (администратор, менеджер и т.д.)
            # Разрешаем чтение
            pass
        
        return super(OpSubjectGrades, self).read(fields, load)

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        # Для совместимости вызываем метод _search с count=False
        res_ids = self._search(args, offset=offset, limit=limit, order=order, count=False)
        return self.browse(res_ids)

    @api.model
    def search_count(self, args, limit=None):
        # Для совместимости вызываем метод _search с count=True
        # Игнорируем параметр limit, так как он не используется в search_count
        return self._search(args, count=True)

    def name_get(self):
        res = []
        for record in self:
            name = "%s - %s" % (record.student_id.name, record.subject_id.name)
            res.append((record.id, name))
        return res

    @api.depends('subject_id', 'batch_id')
    def _compute_textbook_image(self):
        # Collect all subject and batch IDs to perform batch queries
        subject_ids = self.mapped('subject_id').ids
        batch_ids = self.mapped('batch_id').ids

        # Get all media related to the subjects
        all_textbooks = {}
        if subject_ids:
            textbooks = self.env['op.media'].search([
                ('subject_ids', 'in', subject_ids),
                ('x_image_128', '!=', False)
            ])
            
            # Group textbooks by subject_id for faster lookup
            for textbook in textbooks:
                for subject in textbook.subject_ids:
                    if subject.id in subject_ids:
                        if subject.id not in all_textbooks:
                            all_textbooks[subject.id] = []
                        all_textbooks[subject.id].append(textbook)

        # Process each record
        for record in self:
            textbook = None
            
            # Сначала ищем учебник, связанный с предметом и классом студента
            if record.batch_id:
                # Ищем учебники, которые могут быть связаны с конкретным классом
                # Попробуем найти учебник по названию, которое может содержать информацию о классе
                batch_name = record.batch_id.name or ''
                subject_id = record.subject_id.id
                
                if subject_id in all_textbooks:
                    textbooks_for_subject = all_textbooks[subject_id]
                    
                    # Сначала пытаемся найти учебник с точным совпадением по классу в названии
                    for book in textbooks_for_subject:
                        book_name = book.name or ''
                        # Проверяем, содержит ли название учебника информацию о классе
                        if batch_name.lower() in book_name.lower() or \
                           any(str(cls) in book_name for cls in range(1, 12) if str(cls) in batch_name):
                            textbook = book
                            break
                    
                    # Если не нашли учебник с указанием класса, берем первый попавшийся
                    if not textbook and textbooks_for_subject:
                        textbook = textbooks_for_subject[0]
            
            # Если не нашли учебник с учетом класса, ищем любой учебник по предмету
            if not textbook and record.subject_id.id in all_textbooks:
                textbooks_for_subject = all_textbooks[record.subject_id.id]
                if textbooks_for_subject:
                    textbook = textbooks_for_subject[0]
            
            if textbook:
                record.textbook_image = textbook.x_image_128
            else:
                # Если учебник не найден, используем стандартное изображение
                record.textbook_image = False