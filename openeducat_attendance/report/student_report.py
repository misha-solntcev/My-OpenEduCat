from odoo import models, api

class ReportStudentSummary(models.AbstractModel):
    _name = 'report.openeducat_attendance.student_summary_report_template'
    _description = 'Логика итоговой ведомости ученика'

    @api.model
    def _get_report_values(self, docids, data=None):        
        wizard = self.env['student.report.wizard'].browse(docids)
        
        batch = wizard.batch_id
        year = wizard.academic_year_id
        
        # Получаем 4 четверти
        terms = self.env['op.academic.term'].search([
            ('academic_year_id', '=', year.id),
            ('parent_term', '!=', False)
        ], order='term_start_date asc', limit=4)

        # Выборка учеников
        if wizard.student_ids:
            students = wizard.student_ids
        # 2. Если ученики не выбраны, но выбран класс — берем всех учеников класса
        elif wizard.batch_id:
            students = self.env['op.student'].search([
                ('course_detail_ids.batch_id', '=', wizard.batch_id.id)
            ])
        # 3. Если не выбраны ни ученики, ни класс — берем вообще всех учеников (вся школа)
        else:
            students = self.env['op.student'].search([])

        students = students.sorted(key=lambda s: (
            s.course_detail_ids[0].batch_id.sequence if s.course_detail_ids else 999,
            s.name
        ))

        final_data = []
        for student in students:
            # Определяем класс для заголовка
            current_batch = batch or (student.course_detail_ids[0].batch_id if student.course_detail_ids else False)
            if not current_batch: continue

            # Оценки по предметам
            subject_lines = []
            for subject in current_batch.course_id.subject_ids:
                grade_rec = self.env['op.subject.grades'].search([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', subject.id),
                    ('batch_id', '=', current_batch.id)
                ], limit=1)

                subject_lines.append({
                    'name': subject.name,
                    'grades': [grade_rec.q1_final_grade or '', grade_rec.q2_final_grade or '', 
                               grade_rec.q3_final_grade or '', grade_rec.q4_final_grade or ''] if grade_rec else ['', '', '', ''],
                    'year_grade': grade_rec.final_quarter_grade or '' if grade_rec else ''
                })

            # Посещаемость
            attendance_summary = []
            y_total = {'missed': 0, 'sick': 0, 'late': 0}
            for term in terms:
                t_lines = self.env['op.attendance.line'].search([
                    ('student_id', '=', student.id), ('term_id', '=', term.id)])
                
                m = len(t_lines.filtered('absent'))
                s = len(t_lines.filtered('excused'))
                l = len(t_lines.filtered('late'))
                
                attendance_summary.append({'total_missed': m + s, 'sick': s, 'late': l})
                y_total['missed'] += (m + s)
                y_total['sick'] += s
                y_total['late'] += l

            final_data.append({
                'student': student.name,
                'batch': current_batch.name,
                'subjects': subject_lines,
                'attendance': attendance_summary,
                'year_total': y_total,
            })

        return {
            'docs': wizard,
            'student_data': final_data,
            'year': year.name,
        }