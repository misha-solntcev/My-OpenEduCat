from odoo import models, fields, api
from datetime import datetime


class OpSubjectGrades(models.Model):
    _inherit = "op.subject.grades"

    # Добавляем поле для тем уроков
    lesson_topics = fields.Text('Темы уроков')
    
    @api.depends('table_entries')
    def _compute_date_mark_table(self):
        for record in self:
            try:
                if record.table_entries:
                    # Создаем HTML таблицу с центрированными заголовками
                    table_html = '<table class="table table-sm table-bordered">'
                    table_html += '<thead><tr><th style="text-align: center;">Дата</th><th style="text-align: center;">Тема урока</th><th style="text-align: center;">Посещение</th><th style="text-align: center;">Оценка 1</th><th style="text-align: center;">Оценка 2</th><th style="text-align: center;">Комментарий</th></tr></thead><tbody>'
                    
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
                        
                        # Форматируем оценки с использованием цветных бейджей, как в Kanban-представлении, с уменьшенным размером шрифта
                        if mark:
                            if mark == '2':
                                mark_badge = f'<span class="badge fw-bold" style="background-color: #fff0f6; color: #d6336c; font-size: 16px; padding: 4px 8px;">{mark}</span>'
                            elif mark == '3':
                                mark_badge = f'<span class="badge fw-bold" style="background-color: #fff3bf; color: #997404; font-size: 16px; padding: 4px 8px;">{mark}</span>'
                            elif mark == '4':
                                mark_badge = f'<span class="badge fw-bold" style="background-color: #ebfbee; color: #37b24d; font-size: 16px; padding: 4px 8px;">{mark}</span>'
                            elif mark == '5':
                                mark_badge = f'<span class="badge fw-bold" style="background-color: #e7f5ff; color: #1c7ed6; font-size: 16px; padding: 4px 8px;">{mark}</span>'
                            else:
                                mark_badge = f'<span class="badge fw-bold" style="background-color: #f8f9fa; color: #495057; font-size: 16px; padding: 4px 8px;">{mark}</span>'
                        else:
                            mark_badge = ''
                        
                        if behavior:
                            if behavior == '2':
                                behavior_badge = f'<span class="badge fw-bold" style="background-color: #f8f9fa; color: #495057; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
                            elif behavior == '3':
                                behavior_badge = f'<span class="badge fw-bold" style="background-color: #fff3bf; color: #997404; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
                            elif behavior == '4':
                                behavior_badge = f'<span class="badge fw-bold" style="background-color: #ebfbee; color: #37b24d; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
                            elif behavior == '5':
                                behavior_badge = f'<span class="badge fw-bold" style="background-color: #e7f5ff; color: #1c7ed6; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
                            else:
                                behavior_badge = f'<span class="badge fw-bold" style="background-color: #f8f9fa; color: #495057; font-size: 16px; padding: 4px 8px; border: 1px solid #dee2e6;">{behavior}</span>'
                        else:
                            behavior_badge = ''
                        
                        table_html += f'<tr><td style="text-align: center;">{formatted_date}</td><td>{lesson_topic}</td><td style="text-align: center;">{attendance_symbol}</td><td style="text-align: center;">{mark_badge}</td><td style="text-align: center;">{behavior_badge}</td><td>{comment}</td></tr>'
                    
                    table_html += '</tbody></table>'
                    record.date_mark_table = table_html
                else:
                    record.date_mark_table = '<p>Нет данных для отображения</p>'
            except Exception as e:
                # В случае ошибки показываем сообщение об ошибке
                record.date_mark_table = f'<p>Ошибка при отображении таблицы: {str(e)}</p>'