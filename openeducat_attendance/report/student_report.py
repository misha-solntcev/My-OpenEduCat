from odoo import models, api

class ReportStudentSummary(models.AbstractModel):
    _name = 'report.openeducat_attendance.student_summary_report_template'
    _description = 'Логика итоговой ведомости ученика'

    @api.model
    def _get_report_values(self, docids, data=None):
        form = data.get('form')
        batch_id = form.get('batch_id')[0] if form.get('batch_id') else False
        year_id = form.get('academic_year_id')[0]
        
        year = self.env['op.academic.year'].browse(year_id)
        terms = self.env['op.academic.term'].search([
            ('academic_year_id', '=', year.id),
            ('parent_term', '!=', False)
        ], order='term_start_date asc', limit=4)

        # Выборка учеников
        if form.get('student_ids'):
            students = self.env['op.student'].browse(form.get('student_ids'))
        elif batch_id:
            students = self.env['op.student'].search([('course_detail_ids.batch_id', '=', batch_id)])
        else:
            students = self.env['op.student'].search([])

        final_data = []
        for student in students:
            # Определяем текущий класс для заголовка
            current_batch = self.env['op.batch'].browse(batch_id) if batch_id else \
                            (student.course_detail_ids[0].batch_id if student.course_detail_ids else False)
            if not current_batch: continue

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
                m = len(t_lines.filtered(lambda x: x.absent))
                s = len(t_lines.filtered(lambda x: x.excused))
                l = len(t_lines.filtered(lambda x: x.late))
                
                attendance_summary.append({'total_missed': m + s, 'sick': s, 'late': l})
                y_total['missed'] += (m + s)
                y_total['sick'] += s
                y_total['late'] += l

            final_data.append({
                'student': student.name,
                'batch': current_batch.name,
                'year': year.name,
                'subjects': subject_lines,
                'attendance': attendance_summary,
                'year_total': y_total,
                'teacher': getattr(current_batch, 'faculty_id', getattr(current_batch, 'user_id', self.env['res.users'])).name or '________________',
            })

        return {'student_data': final_data}