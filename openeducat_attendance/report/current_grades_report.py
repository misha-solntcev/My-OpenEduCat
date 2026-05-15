from odoo import models, api

class ReportCurrentGrades(models.AbstractModel):
    _name = 'report.openeducat_attendance.current_grades_temp'
    _description = 'Статистика текущих оценок'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['current.grades.report.wizard'].browse(docids)
        
        # 1. Формируем базовый фильтр по датам учебного года (самый надежный способ)
        # Это гарантирует, что мы найдем все оценки года, даже если у них не проставлена четверть
        domain = [
            ('attendance_date', '>=', wizard.academic_year_id.start_date),
            ('attendance_date', '<=', wizard.academic_year_id.end_date)
        ]

        # 2. Добавляем фильтры "Если выбрано"
        if wizard.term_ids:
            domain.append(('term_id', 'in', wizard.term_ids.ids))
        
        if wizard.batch_ids:
            domain.append(('batch_id', 'in', wizard.batch_ids.ids))
        
        if wizard.student_ids:
            domain.append(('student_id', 'in', wizard.student_ids.ids))
            
        if wizard.subject_ids:
            domain.append(('subject_id', 'in', wizard.subject_ids.ids))
        
        # 3. Фильтр: наличие хотя бы одной оценки (убираем пустые строки посещаемости)
        domain += [
            '|', '|', 
            ('grade_1', '>', 0), 
            ('grade_2', '>', 0), 
            ('grade_3', '>', 0)
        ]

        # Находим все подходящие строки
        all_lines = self.env['op.attendance.line'].search(
            domain, 
            order='batch_id, student_id, subject_id, attendance_date asc'
        )

        grouped_data = []
        
        # 4. Группировка данных (используем RecordSet-ы для скорости)
        # Сначала получаем все уникальные классы из найденных строк
        unique_batches = all_lines.mapped('batch_id').sorted('sequence')
        
        for batch in unique_batches:
            batch_lines = all_lines.filtered(lambda l: l.batch_id == batch)
            students_in_batch = batch_lines.mapped('student_id').sorted('name')
            
            student_list = []
            for student in students_in_batch:
                s_lines = batch_lines.filtered(lambda l: l.student_id == student)
                unique_subjects = s_lines.mapped('subject_id').sorted('name')
                
                subject_list = []
                for subject in unique_subjects:
                    sub_lines = s_lines.filtered(lambda l: l.subject_id == subject)
                    
                    marks_data = []
                    for line in sub_lines:
                        # Собираем оценки дня (из всех 3-х колонок)
                        m_vals = [str(int(v)) for v in [line.grade_1, line.grade_2, line.grade_3] if v > 0]
                        if m_vals:
                            marks_data.append({
                                'date': line.attendance_date.strftime('%d.%m'),
                                'val': ", ".join(m_vals)
                            })
                    
                    if marks_data:
                        # Считаем среднее арифметическое именно тех оценок, что вошли в отчет
                        all_marks_in_sub = [v for l in sub_lines for v in [l.grade_1, l.grade_2, l.grade_3] if v > 0]
                        avg_val = sum(all_marks_in_sub) / len(all_marks_in_sub) if all_marks_in_sub else 0
                        
                        subject_list.append({
                            'name': subject.name,
                            'marks': marks_data,
                            'avg': "{:.2f}".format(avg_val)
                        })
                
                if subject_list:
                    student_list.append({
                        'name': student.name,
                        'subjects': subject_list
                    })
            
            if student_list:
                grouped_data.append({
                    'batch': batch.name,
                    'students': student_list
                })

        return {
            'doc_ids': docids,
            'doc_model': 'current.grades.report.wizard',
            'docs': wizard,
            'grouped_data': grouped_data,
            'year_name': wizard.academic_year_id.name,
        }