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
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    student_id = fields.Many2one('op.student', 'Student', required=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    attendance_dates = fields.Text('Attendance Dates')
    marks = fields.Text('Marks')
    behaviors = fields.Text('Behaviors')
    table_entries = fields.Text('Table Entries')  # Новое поле для хранения структурированных данных
    average_mark = fields.Float('Average Mark', compute='_compute_average_mark', store=True)
    total_classes = fields.Integer('Total Classes')
    present_classes = fields.Integer('Present Classes')
    last_attendance_date = fields.Date('Last Attendance Date')
    textbook_image = fields.Binary('Textbook Image', compute='_compute_textbook_image')
    # Новое поле для отображения дат и оценок в виде таблицы
    date_mark_table = fields.Html('Date-Mark Table', compute='_compute_date_mark_table')
    # Новое поле для отображения информации о посещаемости
    attendance_info = fields.Html('Attendance Information', compute='_compute_attendance_info')

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

    @api.depends('table_entries', 'marks', 'behaviors')
    def _compute_average_mark(self):
        for record in self:
            if record.table_entries:
                # Разбираем записи из нового поля table_entries
                entries = [e.strip() for e in record.table_entries.split(',') if e.strip()]
                total_marks = 0
                count = 0
                for entry in entries:
                    parts = entry.split('|')
                    # Оценка 1 находится во втором элементе (индекс 1)
                    if len(parts) >= 2 and parts[1]:
                        try:
                            mark = float(parts[1].strip())
                            total_marks += mark
                            count += 1
                        except ValueError:
                            pass
                    # Оценка 2 (поведение) находится в третьем элементе (индекс 2)
                    if len(parts) >= 3 and parts[2]:
                        try:
                            behavior = float(parts[2].strip())
                            total_marks += behavior
                            count += 1
                        except ValueError:
                            pass
                
                if count > 0:
                    record.average_mark = total_marks / count
                else:
                    record.average_mark = 0.0
            else:
                # Используем старую логику, если table_entries пусто
                all_marks = []
                if record.marks:
                    marks = [m.strip() for m in record.marks.split(',') if m.strip()]
                    for mark in marks:
                        try:
                            all_marks.append(float(mark))
                        except ValueError:
                            pass
                
                if record.behaviors:
                    behaviors = [b.strip() for b in record.behaviors.split(',') if b.strip()]
                    for behavior in behaviors:
                        try:
                            all_marks.append(float(behavior))
                        except ValueError:
                            pass
                
                if all_marks:
                    record.average_mark = sum(all_marks) / len(all_marks)
                else:
                    record.average_mark = 0.0

    @api.depends('table_entries')
    def _compute_date_mark_table(self):
        for record in self:
            _logger.info("Computing date_mark_table for record id=%s, student=%s, subject=%s", 
                        record.id, record.student_id.name if record.student_id else 'None', 
                        record.subject_id.name if record.subject_id else 'None')
            _logger.info("table_entries content: %s", record.table_entries)
            
            if record.table_entries:
                # Создаем HTML таблицу
                table_html = '<table class="table table-sm table-bordered">'
                table_html += '<thead><tr><th>Дата</th><th>Присутствует</th><th>Опоздал</th><th>Отсутствует по уважительной причине</th><th>Прогул</th><th>Оценка 1</th><th>Оценка 2</th><th>Комментарий</th></tr></thead><tbody>'
                
                # Разбираем записи таблицы
                entries = [e.strip() for e in record.table_entries.split(',') if e.strip()]
                _logger.info("Parsed entries: %s", entries)
                
                # Заполняем таблицу данными
                for entry in entries:
                    parts = entry.split('|')
                    _logger.info("Entry parts: %s", parts)
                    date = parts[0] if len(parts) > 0 and parts[0] else ''
                    mark = parts[1] if len(parts) > 1 and parts[1] else ''
                    behavior = parts[2] if len(parts) > 2 and parts[2] else ''
                    
                    # Получаем информацию о посещаемости из записи
                    present_raw = parts[3] if len(parts) > 3 and parts[3] else ''
                    late_raw = parts[4] if len(parts) > 4 and parts[4] else ''
                    absent_raw = parts[5] if len(parts) > 5 and parts[5] else ''
                    unexcused_absent_raw = parts[6] if len(parts) > 6 and parts[6] else ''
                    comment = parts[7] if len(parts) > 7 and parts[7] else ''
                    
                    # Формируем визуальные галочки с использованием HTML-элементов
                    present_display = '<span style="color: green; font-weight: bold; font-size: 18px;">✓</span>' if present_raw and present_raw.strip() == '✓' else '<span style="color: lightgray; font-size: 18px;">○</span>'
                    late_display = '<span style="color: orange; font-weight: bold; font-size: 18px;">✓</span>' if late_raw and late_raw.strip() == '✓' else '<span style="color: lightgray; font-size: 18px;">○</span>'
                    absent_display = '<span style="color: blue; font-weight: bold; font-size: 18px;">✓</span>' if absent_raw and absent_raw.strip() == '✓' else '<span style="color: lightgray; font-size: 18px;">○</span>'
                    unexcused_absent_display = '<span style="color: red; font-weight: bold; font-size: 18px;">✓</span>' if unexcused_absent_raw and unexcused_absent_raw.strip() == '✓' else '<span style="color: lightgray; font-size: 18px;">○</span>'
                    
                    table_html += f'<tr><td>{date}</td><td>{present_display}</td><td>{late_display}</td><td>{absent_display}</td><td>{unexcused_absent_display}</td><td>{mark}</td><td>{behavior}</td><td>{comment}</td></tr>'
                
                table_html += '</tbody></table>'
                record.date_mark_table = table_html
            else:
                record.date_mark_table = '<p>Нет данных для отображения</p>'

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

    @api.depends('student_id', 'subject_id', 'batch_id')
    def _compute_attendance_info(self):
        for record in self:
            if record.student_id and record.subject_id:
                # Получаем все записи посещаемости для студента по данному предмету
                attendance_lines = self.env['op.attendance.line'].search([
                    ('student_id', '=', record.student_id.id),
                    ('x_subject', '=', str(record.subject_id.id))
                ])
                
                # Считаем общее количество занятий и количество посещений
                total_classes = len(attendance_lines)
                present_classes = len(attendance_lines.filtered(lambda r: r.present))
                
                # Создаем HTML таблицу с информацией о посещаемости
                table_html = '<table class="table table-sm table-bordered">'
                table_html += '<thead><tr><th>Дата</th><th>Статус</th><th>Комментарий</th></tr></thead><tbody>'
                
                # Добавляем строки для каждого занятия
                for line in attendance_lines:
                    status = 'Неизвестно'
                    if line.present:
                        status = 'Присутствовал'
                    elif line.absent:
                        status = 'Отсутствовал'
                    elif line.late:
                        status = 'Опоздал'
                    elif line.excused:
                        status = 'Отсутствовал (уважительная причина)'
                    
                    table_html += f'<tr><td>{line.attendance_date or ""}</td><td>{status}</td><td>{line.remark or ""}</td></tr>'
                
                table_html += '</tbody></table>'
                
                # Добавляем сводную информацию
                summary_html = f'<div class="row">'
                summary_html += f'<div class="col-md-6"><strong>Всего занятий:</strong> {total_classes}</div>'
                summary_html += f'<div class="col-md-6"><strong>Посетил занятий:</strong> {present_classes}</div>'
                summary_html += f'</div><br/>'
                
                record.attendance_info = summary_html + table_html
            else:
                record.attendance_info = '<p>Нет данных о посещаемости</p>'
