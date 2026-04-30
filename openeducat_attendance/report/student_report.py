# addons/openeducat_attendance/report/student_report.py

from odoo import models, api

class ReportStudentSummary(models.AbstractModel):
    _name = 'report.openeducat_attendance.student_summary_report_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['student.report.wizard'].browse(docids)
        year = wizard.academic_year_id
        
        # 1. Получаем четверти
        terms = self.env['op.academic.term'].search([
            ('academic_year_id', '=', year.id),
            ('parent_term', '!=', False)
        ], order='term_start_date asc', limit=4)

        # 2. Определяем, какие классы мы печатаем
        if wizard.batch_id:
            batches = wizard.batch_id
        elif wizard.student_ids:
            # Если выбраны конкретные ученики, находим их уникальные классы
            batches = wizard.student_ids.mapped('course_detail_ids.batch_id').sorted('sequence')
        else:
            # Вся школа — берем все классы, сортируем по вашему sequence
            batches = self.env['op.batch'].search([], order='sequence')

        grouped_data = []

        for batch in batches:
            # Выбираем учеников для этого конкретного класса
            if wizard.student_ids:
                # Только тех из выбранных, кто в этом классе
                students_in_batch = wizard.student_ids.filtered(
                    lambda s: any(c.batch_id == batch for c in s.course_detail_ids)
                ).sorted('name')
            else:
                # Всех учеников этого класса
                students_in_batch = self.env['op.student'].search([
                    ('course_detail_ids.batch_id', '=', batch.id)
                ], order='name')

            if not students_in_batch:
                continue

            student_list = []
            for student in students_in_batch:
                # Собираем оценки (ваш существующий код внутри цикла)
                subject_lines = []
                for subject in batch.course_id.subject_ids:
                    grade_rec = self.env['op.subject.grades'].search([
                        ('student_id', '=', student.id),
                        ('subject_id', '=', subject.id),
                        ('batch_id', '=', batch.id)
                    ], limit=1)

                    subject_lines.append({
                        'name': subject.name,
                        'grades': [grade_rec.q1_final_grade or '', grade_rec.q2_final_grade or '', 
                                   grade_rec.q3_final_grade or '', grade_rec.q4_final_grade or ''] if grade_rec else ['', '', '', ''],
                        'year_grade': grade_rec.final_quarter_grade or '' if grade_rec else ''
                    })

                # Собираем посещаемость
                y_total = {'missed': 0, 'sick': 0, 'late': 0}
                att_summary = []
                for term in terms:
                    t_lines = self.env['op.attendance.line'].search([
                        ('student_id', '=', student.id), ('term_id', '=', term.id)])
                    m, s, l = len(t_lines.filtered('absent')), len(t_lines.filtered('excused')), len(t_lines.filtered('late'))
                    att_summary.append({'total_missed': m + s, 'sick': s, 'late': l})
                    y_total['missed'] += (m + s); y_total['sick'] += s; y_total['late'] += l

                student_list.append({
                    'student': student.name,
                    'subjects': subject_lines,
                    'attendance': att_summary,
                    'year_total': y_total,
                })

            grouped_data.append({
                'batch_name': batch.name,
                'students': student_list,
            })

        return {
            'docs': wizard,
            'grouped_data': grouped_data,
            'year': year.name,
        }