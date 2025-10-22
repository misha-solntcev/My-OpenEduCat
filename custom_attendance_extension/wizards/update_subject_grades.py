from odoo import models, fields, api


class UpdateSubjectGrades(models.TransientModel):
    _inherit = 'update.subject.grades'

    def update_grades(self):
        # Вызываем оригинальный метод
        result = super().update_grades()
        
        # Обрабатываем темы уроков
        subject_grade_obj = self.env['op.subject.grades']
        
        # Получаем записи посещаемости
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