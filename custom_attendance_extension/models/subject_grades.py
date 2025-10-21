from odoo import models, fields, api


class OpSubjectGrades(models.Model):
    _inherit = "op.subject.grades"

    # Добавляем поле для тем уроков
    lesson_topics = fields.Text('Темы уроков')
    
    @api.depends('table_entries', 'lesson_topics')
    def _compute_date_mark_table(self):
        for record in self:
            if record.table_entries:
                # Создаем HTML таблицу
                table_html = '<table class="table table-sm table-bordered">'
                table_html += '<thead><tr><th>Дата</th><th>Тема урока</th><th>Посещение</th><th>Оценка 1</th><th>Оценка 2</th><th>Комментарий</th></tr></thead><tbody>'
                
                # Разбираем записи таблицы
                entries = [e.strip() for e in record.table_entries.split(',') if e.strip()]
                
                # Разбираем темы уроков
                lesson_topics_dict = {}
                if record.lesson_topics:
                    for line in record.lesson_topics.split('\n'):
                        if ':' in line:
                            date_part, topic_part = line.split(':', 1)
                            lesson_topics_dict[date_part.strip()] = topic_part.strip()
                
                # Заполняем таблицу данными
                for entry in entries:
                    parts = entry.split('|')
                    date = parts[0] if len(parts) > 0 and parts[0] else ''
                    mark = parts[1] if len(parts) > 1 and parts[1] else ''
                    behavior = parts[2] if len(parts) > 2 and parts[2] else ''
                    
                    # Получаем информацию о посещаемости из записи
                    present_raw = parts[3] if len(parts) > 3 and parts[3] else ''
                    late_raw = parts[4] if len(parts) > 4 and parts[4] else ''
                    absent_raw = parts[5] if len(parts) > 5 and parts[5] else ''
                    unexcused_absent_raw = parts[6] if len(parts) > 6 and parts[6] else ''
                    comment = parts[7] if len(parts) > 7 and parts[7] else ''
                    
                    # Получаем тему урока для этой даты
                    lesson_topic = lesson_topics_dict.get(date, '') if date else ''
                    
                    # Определяем символ посещаемости на основе типов из op.attendance.type с улучшенным оформлением
                    if present_raw and present_raw.strip() == '✓':
                        # Присутствует - зеленая иконка галочки
                        attendance_symbol = '<i class="fa fa-check" style="color: green; font-size: 18px;"></i>'
                    elif late_raw and late_raw.strip() == '✓':
                        # Опоздал - оранжевая иконка часов
                        attendance_symbol = '<i class="fa fa-clock-o" style="color: orange; font-size: 18px;"></i>'
                    elif absent_raw and absent_raw.strip() == '✓':
                        if unexcused_absent_raw and unexcused_absent_raw.strip() == '✓':
                            # Прогул - красная иконка крестика
                            attendance_symbol = '<i class="fa fa-times" style="color: red; font-size: 18px;"></i>'
                        else:
                            # Отсутствует по уважительной причине - синяя иконка документа
                            attendance_symbol = '<i class="fa fa-file-text" style="color: blue; font-size: 18px;"></i>'
                    else:
                        # Не определено - серая иконка вопроса
                        attendance_symbol = '<i class="fa fa-question" style="color: lightgray; font-size: 18px;"></i>'
                    
                    # Форматируем оценки с использованием бейджей
                    mark_badge = f'<span class="badge" style="background-color: #007bff; font-size: 12px; padding: 4px 8px;">{mark}</span>' if mark else ''
                    behavior_badge = f'<span class="badge" style="background-color: #28a745; font-size: 12px; padding: 4px 8px;">{behavior}</span>' if behavior else ''
                    
                    table_html += f'<tr><td>{date}</td><td>{lesson_topic}</td><td style="text-align: center;">{attendance_symbol}</td><td style="text-align: center;">{mark_badge}</td><td style="text-align: center;">{behavior_badge}</td><td>{comment}</td></tr>'
                
                table_html += '</tbody></table>'
                record.date_mark_table = table_html
            else:
                record.date_mark_table = '<p>Нет данных для отображения</p>'