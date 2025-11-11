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
from datetime import datetime

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
    # Поле для ручного ввода итоговой оценки за четверть
    final_quarter_grade = fields.Char('Итоговая оценка за четверть')
    
    # Добавляем поле для тем уроков (резервное решение)
    lesson_topics = fields.Text(
        'Темы уроков', 
        help="Темы уроков по данному предмету"
    )
    
    # Вычисляемые поля для таблиц по четвертям
    date_mark_table_q1 = fields.Html('Date-Mark Table Q1', compute='_compute_date_mark_table_q1')
    date_mark_table_q2 = fields.Html('Date-Mark Table Q2', compute='_compute_date_mark_table_q2')
    date_mark_table_q3 = fields.Html('Date-Mark Table Q3', compute='_compute_date_mark_table_q3')
    date_mark_table_q4 = fields.Html('Date-Mark Table Q4', compute='_compute_date_mark_table_q4')
    
    # Добавляем вычисляемые поля для отображения информации по четвертям
    q1_total_classes = fields.Integer('Q1 Total Classes', compute='_compute_q1_data')
    q1_present_classes = fields.Integer('Q1 Present Classes', compute='_compute_q1_data')
    q1_last_attendance_date = fields.Date('Q1 Last Attendance Date', compute='_compute_q1_data')
    q1_average_mark = fields.Float('Q1 Average Mark', compute='_compute_q1_data')
    
    q2_total_classes = fields.Integer('Q2 Total Classes', compute='_compute_q2_data')
    q2_present_classes = fields.Integer('Q2 Present Classes', compute='_compute_q2_data')
    q2_last_attendance_date = fields.Date('Q2 Last Attendance Date', compute='_compute_q2_data')
    q2_average_mark = fields.Float('Q2 Average Mark', compute='_compute_q2_data')
    
    q3_total_classes = fields.Integer('Q3 Total Classes', compute='_compute_q3_data')
    q3_present_classes = fields.Integer('Q3 Present Classes', compute='_compute_q3_data')
    q3_last_attendance_date = fields.Date('Q3 Last Attendance Date', compute='_compute_q3_data')
    q3_average_mark = fields.Float('Q3 Average Mark', compute='_compute_q3_data')
    
    q4_total_classes = fields.Integer('Q4 Total Classes', compute='_compute_q4_data')
    q4_present_classes = fields.Integer('Q4 Present Classes', compute='_compute_q4_data')
    q4_last_attendance_date = fields.Date('Q4 Last Attendance Date', compute='_compute_q4_data')
    q4_average_mark = fields.Float('Q4 Average Mark', compute='_compute_q4_data')

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
        
        # Для студентов всегда применяем фильтрацию
        if is_student and len(self) == 1:  # Проверяем, что работаем с одной записью
            # Пользователь в группе студентов, проверим, связан ли он со студентом
            student_record = self.env['op.student'].search([('user_id', '=', self.env.user.id)], limit=1)
            # Проверяем, что запись существует и не пустая
            if student_record and student_record.id:
                try:
                    # Проверяем, принадлежит ли запись студенту
                    if self.student_id.id != student_record.id:
                        # Если запись не принадлежит студенту, возвращаем пустой результат
                        return []
                except Exception:
                    # В случае ошибки (например, множественная запись) пропускаем проверку
                    pass
        
        return super(OpSubjectGrades, self).read(fields=fields, load=load)

    @api.depends('marks', 'behaviors')
    def _compute_average_mark(self):
        for record in self:
            all_marks = []
            if record.marks:
                for mark in record.marks.split(','):
                    try:
                        mark_val = float(mark.strip())
                        all_marks.append(mark_val)
                    except ValueError:
                        pass
            if record.behaviors:
                for behavior in record.behaviors.split(','):
                    try:
                        behavior_val = float(behavior.strip())
                        all_marks.append(behavior_val)
                    except ValueError:
                        pass
            if all_marks:
                record.average_mark = sum(all_marks) / len(all_marks)
            else:
                record.average_mark = 0.0

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
            if record.batch_id and record.batch_id.course_id:
                # Получаем курс (класс) студента
                course_id = record.batch_id.course_id.id
                
                # Ищем учебники, которые связаны с этим курсом и предметом
                subject_id = record.subject_id.id
                
                if subject_id in all_textbooks:
                    textbooks_for_subject = all_textbooks[subject_id]
                    
                    # Сначала пытаемся найти учебник, который связан с конкретным курсом
                    for book in textbooks_for_subject:
                        if course_id in book.course_ids.ids:
                            textbook = book
                            break
                    
                    # Если не нашли учебник с учетом курса, ищем любой учебник по предмету
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

    @api.depends('table_entries', 'lesson_topics')
    def _compute_date_mark_table(self):
        """
        Вычисляет HTML-таблицу с оценками и посещаемостью по датам.
        Включает отображение тем уроков.
        """
        for record in self:
            try:
                if record.table_entries:
                    # Создаем HTML таблицу с центрированными заголовками
                    table_html = '''
<table class="table table-sm table-bordered">
    <thead>
        <tr>
            <th style="text-align: center;">Дата</th>
            <th style="text-align: center;">Тема урока</th>
            <th style="text-align: center;">Посещение</th>
            <th style="text-align: center;">Оценка 1</th>
            <th style="text-align: center;">Оценка 2</th>
            <th style="text-align: center;">Комментарий</th>
        </tr>
    </thead>
    <tbody>'''
                    
                    # Разбираем записи таблицы
                    entries = [e.strip() for e in record.table_entries.split(',') if e.strip()]
                    
                    # Заполняем таблицу данными
                    for entry in entries:
                        parts = entry.split('|')
                        date = parts[0] if len(parts) > 0 and parts[0] else ''
                        mark = parts[1] if len(parts) > 1 and parts[1] else ''
                        behavior = parts[2] if len(parts) > 2 and parts[2] else ''
                        
                        # Преобразуем формат даты из ГГГГ-ММ-ДД в ДД.ММ.ГГГГ
                        formatted_date = date
                        if date:
                            try:
                                date_obj = datetime.strptime(date, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%d.%m.%Y')
                            except ValueError:
                                # Если не удалось преобразовать, оставляем как есть
                                pass
                        
                        # Получаем информацию о посещаемости из записи
                        present_raw = parts[3] if len(parts) > 3 and parts[3] else ''
                        late_raw = parts[4] if len(parts) > 4 and parts[4] else ''
                        absent_raw = parts[5] if len(parts) > 5 and parts[5] else ''
                        unexcused_absent_raw = parts[6] if len(parts) > 6 and parts[6] else ''
                        comment = parts[7] if len(parts) > 7 and parts[7] else ''
                        
                        # Получаем тему урока из записи
                        lesson_topic = parts[8] if len(parts) > 8 and parts[8] else ''
                        
                        # Определяем символ посещаемости
                        attendance_symbol = self._get_attendance_symbol(
                            present_raw, late_raw, absent_raw, unexcused_absent_raw)
                        
                        # Форматируем оценки
                        mark_badge = self._format_mark(mark)
                        behavior_badge = self._format_behavior(behavior)
                        
                        table_html += f'''
        <tr>
            <td style="text-align: center;">{formatted_date}</td>
            <td>{lesson_topic}</td>
            <td style="text-align: center;">{attendance_symbol}</td>
            <td style="text-align: center;">{mark_badge}</td>
            <td style="text-align: center;">{behavior_badge}</td>
            <td>{comment}</td>
        </tr>'''
                    
                    table_html += '''
    </tbody>
</table>'''
                    
                    # Добавляем легенду с объяснением символов по центру
                    table_html += '''
<div style="margin-top: 15px; display: flex; flex-wrap: wrap; justify-content: center; gap: 15px;">
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-check" style="color: green; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Присутствует</span>
    </div>
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-clock-o" style="color: orange; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Опоздал</span>
    </div>
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-file-text" style="color: blue; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Отсутствует по уважительной причине</span>
    </div>
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-times" style="color: red; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Прогул</span>
    </div>
</div>'''
                    
                    record.date_mark_table = table_html
                else:
                    record.date_mark_table = '<p>Нет данных для отображения</p>'
            except Exception as e:
                _logger.error("Ошибка при вычислении таблицы оценок: %s", str(e))
                record.date_mark_table = f'<p>Ошибка при отображении таблицы: {str(e)}</p>'

    def _get_attendance_symbol(self, present_raw, late_raw, absent_raw, unexcused_absent_raw):
        """
        Возвращает HTML-код символа посещаемости на основе данных
        
        Args:
            present_raw (str): Признак присутствия
            late_raw (str): Признак опоздания
            absent_raw (str): Признак отсутствия
            unexcused_absent_raw (str): Признак прогула
            
        Returns:
            str: HTML-код символа посещаемости
        """
        if present_raw and present_raw.strip() == '✓':
            # Присутствует - зеленая иконка галочки
            return '<i class="fa fa-check" style="color: green; font-size: 18px;"></i>'
        elif late_raw and late_raw.strip() == '✓':
            # Опоздал - оранжевая иконка часов
            return '<i class="fa fa-clock-o" style="color: orange; font-size: 18px;"></i>'
        elif absent_raw and absent_raw.strip() == '✓':
            if unexcused_absent_raw and unexcused_absent_raw.strip() == '✓':
                # Прогул - красная иконка крестика
                return '<i class="fa fa-times" style="color: red; font-size: 18px;"></i>'
            else:
                # Отсутствует по уважительной причине - синяя иконка документа
                return '<i class="fa fa-file-text" style="color: blue; font-size: 18px;"></i>'
        else:
            # Не определено - серая иконка вопроса
            return '<i class="fa fa-question" style="color: lightgray; font-size: 18px;"></i>'

    def _format_mark(self, mark):
        """
        Форматирует оценку как цветной бейдж
        
        Args:
            mark (str): Значение оценки
            
        Returns:
            str: HTML-код бейджа с оценкой
        """
        if not mark:
            return ''
            
        # Форматируем оценки с использованием цветных бейджей
        if mark == '2':
            return f'<span class="badge fw-bold" style="background-color: #fff0f6; color: #d6336c; font-size: 16px; padding: 4px 8px;">{mark}</span>'
        elif mark == '3':
            return f'<span class="badge fw-bold" style="background-color: #fff3bf; color: #997404; font-size: 16px; padding: 4px 8px;">{mark}</span>'
        elif mark == '4':
            return f'<span class="badge fw-bold" style="background-color: #ebfbee; color: #37b24d; font-size: 16px; padding: 4px 8px;">{mark}</span>'
        elif mark == '5':
            return f'<span class="badge fw-bold" style="background-color: #e7f5ff; color: #1c7ed6; font-size: 16px; padding: 4px 8px;">{mark}</span>'
        else:
            return f'<span class="badge fw-bold" style="background-color: #f8f9fa; color: #495057; font-size: 16px; padding: 4px 8px;">{mark}</span>'

    def _format_behavior(self, behavior):
        """
        Форматирует поведение как цветной бейдж
        
        Args:
            behavior (str): Значение поведения
            
        Returns:
            str: HTML-код бейджа с поведением
        """
        if not behavior:
            return ''
            
        # Форматируем поведение с использованием цветных бейджей
        if behavior == '2':
            return f'<span class="badge fw-bold" style="background-color: #f8f9fa; color: #495057; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
        elif behavior == '3':
            return f'<span class="badge fw-bold" style="background-color: #fff3bf; color: #997404; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
        elif behavior == '4':
            return f'<span class="badge fw-bold" style="background-color: #ebfbee; color: #37b24d; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
        elif behavior == '5':
            return f'<span class="badge fw-bold" style="background-color: #e7f5ff; color: #1c7ed6; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
        else:
            return f'<span class="badge fw-bold" style="background-color: #f8f9fa; color: #495057; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
        
    def _get_quarter_dates(self, quarter):
        """
        Возвращает начальную и конечную даты для заданной четверти.
        В учебном году 4 четверти:
        1 четверть: 1 сентября - 31 октября
        2 четверть: 1 ноября - 25 декабря
        3 четверть: 11 января - 28 марта
        4 четверть: 1 апреля - 31 мая
        
        Args:
            quarter (int): Номер четверти (1-4)
            
        Returns:
            tuple: (start_date, end_date) в формате datetime
        """
        year = datetime.now().year
        
        if quarter == 1:
            start_date = datetime(year, 9, 1)
            end_date = datetime(year, 10, 31)
        elif quarter == 2:
            start_date = datetime(year, 11, 1)
            end_date = datetime(year, 12, 25)
        elif quarter == 3:
            start_date = datetime(year, 1, 11)
            end_date = datetime(year, 3, 28)
        elif quarter == 4:
            start_date = datetime(year, 4, 1)
            end_date = datetime(year, 5, 31)
        else:
            # По умолчанию возвращаем весь год
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
            
        return start_date, end_date
    
    def _filter_entries_by_quarter(self, entries, quarter):
        """
        Фильтрует записи по заданной четверти.
        
        Args:
            entries (list): Список записей в формате строк
            quarter (int): Номер четверти (1-4)
            
        Returns:
            list: Отфильтрованный список записей
        """
        if not entries:
            return []
            
        start_date, end_date = self._get_quarter_dates(quarter)
        
        filtered_entries = []
        for entry in entries:
            parts = entry.split('|')
            if len(parts) > 0 and parts[0]:
                try:
                    # Преобразуем дату из строки
                    date_obj = datetime.strptime(parts[0], '%Y-%m-%d')
                    # Проверяем, попадает ли дата в диапазон четверти
                    if start_date <= date_obj <= end_date:
                        filtered_entries.append(entry)
                except ValueError:
                    # Если не удалось преобразовать дату, пропускаем запись
                    pass
                    
        return filtered_entries
    
    def _compute_date_mark_table_quarter(self, quarter):
        """
        Вычисляет HTML-таблицу с оценками и посещаемостью по датам для заданной четверти.
        
        Args:
            quarter (int): Номер четверти (1-4)
            
        Returns:
            str: HTML-код таблицы
        """
        self.ensure_one()
        try:
            if self.table_entries:
                # Создаем HTML таблицу с центрированными заголовками
                table_html = '''
<table class="table table-sm table-bordered">
    <thead>
        <tr>
            <th style="text-align: center;">Дата</th>
            <th style="text-align: center;">Тема урока</th>
            <th style="text-align: center;">Посещение</th>
            <th style="text-align: center;">Оценка 1</th>
            <th style="text-align: center;">Оценка 2</th>
            <th style="text-align: center;">Комментарий</th>
        </tr>
    </thead>
    <tbody>'''
                
                # Разбираем записи таблицы
                entries = [e.strip() for e in self.table_entries.split(',') if e.strip()]
                
                # Фильтруем записи по четверти
                quarter_entries = self._filter_entries_by_quarter(entries, quarter)
                
                # Заполняем таблицу данными
                for entry in quarter_entries:
                    parts = entry.split('|')
                    date = parts[0] if len(parts) > 0 and parts[0] else ''
                    mark = parts[1] if len(parts) > 1 and parts[1] else ''
                    behavior = parts[2] if len(parts) > 2 and parts[2] else ''
                    
                    # Преобразуем формат даты из ГГГГ-ММ-ДД в ДД.ММ.ГГГГ
                    formatted_date = date
                    if date:
                        try:
                            date_obj = datetime.strptime(date, '%Y-%m-%d')
                            formatted_date = date_obj.strftime('%d.%m.%Y')
                        except ValueError:
                            # Если не удалось преобразовать, оставляем как есть
                            pass
                    
                    # Получаем информацию о посещаемости из записи
                    present_raw = parts[3] if len(parts) > 3 and parts[3] else ''
                    late_raw = parts[4] if len(parts) > 4 and parts[4] else ''
                    absent_raw = parts[5] if len(parts) > 5 and parts[5] else ''
                    unexcused_absent_raw = parts[6] if len(parts) > 6 and parts[6] else ''
                    comment = parts[7] if len(parts) > 7 and parts[7] else ''
                    
                    # Получаем тему урока из записи
                    lesson_topic = parts[8] if len(parts) > 8 and parts[8] else ''
                    
                    # Определяем символ посещаемости
                    attendance_symbol = self._get_attendance_symbol(
                        present_raw, late_raw, absent_raw, unexcused_absent_raw)
                    
                    # Форматируем оценки
                    mark_badge = self._format_mark(mark)
                    behavior_badge = self._format_behavior(behavior)
                    
                    table_html += f'''
        <tr>
            <td style="text-align: center;">{formatted_date}</td>
            <td>{lesson_topic}</td>
            <td style="text-align: center;">{attendance_symbol}</td>
            <td style="text-align: center;">{mark_badge}</td>
            <td style="text-align: center;">{behavior_badge}</td>
            <td>{comment}</td>
        </tr>'''
                
                table_html += '''
    </tbody>
</table>'''
                
                # Добавляем легенду с объяснением символов по центру
                table_html += '''
<div style="margin-top: 15px; display: flex; flex-wrap: wrap; justify-content: center; gap: 15px;">
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-check" style="color: green; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Присутствует</span>
    </div>
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-clock-o" style="color: orange; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Опоздал</span>
    </div>
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-file-text" style="color: blue; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Отсутствует по уважительной причине</span>
    </div>
    <div style="display: flex; align-items: center; min-width: 150px;">
        <i class="fa fa-times" style="color: red; font-size: 18px; width: 20px; text-align: center;"></i>
        <span style="margin-left: 5px;">Прогул</span>
    </div>
</div>'''
                
                return table_html
            else:
                return '<p>Нет данных для отображения</p>'
        except Exception as e:
            _logger.error("Ошибка при вычислении таблицы оценок: %s", str(e))
            return f'<p>Ошибка при отображении таблицы: {str(e)}</p>'
    
    @api.depends('table_entries', 'lesson_topics')
    def _compute_date_mark_table_q1(self):
        """Вычисляет таблицу для 1 четверти"""
        for record in self:
            record.date_mark_table_q1 = record._compute_date_mark_table_quarter(1)
            
    @api.depends('table_entries', 'lesson_topics')
    def _compute_date_mark_table_q2(self):
        """Вычисляет таблицу для 2 четверти"""
        for record in self:
            record.date_mark_table_q2 = record._compute_date_mark_table_quarter(2)
            
    @api.depends('table_entries', 'lesson_topics')
    def _compute_date_mark_table_q3(self):
        """Вычисляет таблицу для 3 четверти"""
        for record in self:
            record.date_mark_table_q3 = record._compute_date_mark_table_quarter(3)
            
    @api.depends('table_entries', 'lesson_topics')
    def _compute_date_mark_table_q4(self):
        """Вычисляет таблицу для 4 четверти"""
        for record in self:
            record.date_mark_table_q4 = record._compute_date_mark_table_quarter(4)
            
    def _compute_quarter_data(self, quarter):
        """
        Вычисляет данные по заданной четверти
        
        Args:
            quarter (int): Номер четверти (1-4)
            
        Returns:
            dict: Словарь с данными по четверти
        """
        self.ensure_one()
        result = {
            'total_classes': 0,
            'present_classes': 0,
            'last_attendance_date': False,
            'average_mark': 0.0
        }
        
        if not self.table_entries:
            return result
            
        try:
            # Разбираем записи таблицы
            entries = [e.strip() for e in self.table_entries.split(',') if e.strip()]
            
            # Фильтруем записи по четверти
            quarter_entries = self._filter_entries_by_quarter(entries, quarter)
            
            if not quarter_entries:
                return result
                
            # Подсчитываем общее количество занятий
            result['total_classes'] = len(quarter_entries)
            
            # Подсчитываем посещенные занятия и собираем оценки
            present_count = 0
            marks_sum = 0
            marks_count = 0
            last_date = None
            
            for entry in quarter_entries:
                parts = entry.split('|')
                if len(parts) == 0:
                    continue
                    
                # Обрабатываем дату
                date_str = parts[0] if len(parts) > 0 and parts[0] else ''
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        if not last_date or date_obj > last_date:
                            last_date = date_obj
                    except ValueError:
                        pass
                
                # Проверяем посещение
                present_raw = parts[3] if len(parts) > 3 and parts[3] else ''
                if present_raw and present_raw.strip() == '✓':
                    present_count += 1
                
                # Собираем оценки
                # Оценка 1
                mark1 = parts[1] if len(parts) > 1 and parts[1] else ''
                if mark1:
                    try:
                        marks_sum += float(mark1.strip())
                        marks_count += 1
                    except ValueError:
                        pass
                
                # Оценка 2 (поведение)
                mark2 = parts[2] if len(parts) > 2 and parts[2] else ''
                if mark2:
                    try:
                        marks_sum += float(mark2.strip())
                        marks_count += 1
                    except ValueError:
                        pass
            
            result['present_classes'] = present_count
            result['last_attendance_date'] = last_date.date() if last_date else False
            
            # Вычисляем среднюю оценку
            if marks_count > 0:
                result['average_mark'] = round(marks_sum / marks_count, 2)
                
        except Exception as e:
            _logger.error("Ошибка при вычислении данных по четверти: %s", str(e))
            
        return result
    
    @api.depends('table_entries', 'lesson_topics')
    def _compute_q1_data(self):
        """Вычисляет данные для 1 четверти"""
        for record in self:
            data = record._compute_quarter_data(1)
            record.q1_total_classes = data['total_classes']
            record.q1_present_classes = data['present_classes']
            record.q1_last_attendance_date = data['last_attendance_date']
            record.q1_average_mark = data['average_mark']
            
    @api.depends('table_entries', 'lesson_topics')
    def _compute_q2_data(self):
        """Вычисляет данные для 2 четверти"""
        for record in self:
            data = record._compute_quarter_data(2)
            record.q2_total_classes = data['total_classes']
            record.q2_present_classes = data['present_classes']
            record.q2_last_attendance_date = data['last_attendance_date']
            record.q2_average_mark = data['average_mark']
            
    @api.depends('table_entries', 'lesson_topics')
    def _compute_q3_data(self):
        """Вычисляет данные для 3 четверти"""
        for record in self:
            data = record._compute_quarter_data(3)
            record.q3_total_classes = data['total_classes']
            record.q3_present_classes = data['present_classes']
            record.q3_last_attendance_date = data['last_attendance_date']
            record.q3_average_mark = data['average_mark']
            
    @api.depends('table_entries', 'lesson_topics')
    def _compute_q4_data(self):
        """Вычисляет данные для 4 четверти"""
        for record in self:
            data = record._compute_quarter_data(4)
            record.q4_total_classes = data['total_classes']
            record.q4_present_classes = data['present_classes']
            record.q4_last_attendance_date = data['last_attendance_date']
            record.q4_average_mark = data['average_mark']
