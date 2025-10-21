from odoo import models, fields, api


class UpdateSubjectGrades(models.TransientModel):
    _inherit = 'update.subject.grades'

    def update_grades(self):
        # Сначала вызываем оригинальный метод
        result = super(UpdateSubjectGrades, self).update_grades()
        
        # Затем добавляем обработку тем уроков
        subject_grade_obj = self.env['op.subject.grades']
        
        # Получаем все записи посещаемости для обработки тем уроков
        attendance_sheets = self.env['op.attendance.sheet'].search([
            ('attendance_date', '>=', self.start_date),
            ('attendance_date', '<=', self.end_date),
        ])
        
        # Группируем темы уроков по студентам и предметам
        lesson_topics_data = {}
        for sheet in attendance_sheets:
            if sheet.lesson_topic:  # Если указана тема урока
                # Получаем регистр посещаемости для получения информации о предмете
                register = sheet.register_id
                subject_id = register.subject_id.id if register.subject_id else None
                
                if subject_id:
                    # Для каждой строки посещаемости (по студентам)
                    for line in sheet.attendance_line:
                        student_id = line.student_id.id
                        key = (student_id, subject_id)
                        
                        if key not in lesson_topics_data:
                            lesson_topics_data[key] = []
                            
                        # Добавляем тему урока с датой
                        lesson_topics_data[key].append("%s (%s)" % (sheet.lesson_topic, sheet.attendance_date))
        
        # Обновляем записи предметных оценок с темами уроков
        for (student_id, subject_id), topics in lesson_topics_data.items():
            # Ищем существующую запись
            record = subject_grade_obj.search([
                ('student_id', '=', student_id),
                ('subject_id', '=', subject_id),
                ('batch_id', '=', self.batch_id.id)
            ], limit=1)
            
            if record:
                # Обновляем существующую запись
                topics_str = ', '.join(topics)
                record.write({'lesson_topics': topics_str})
        
        return result