from odoo import models, api

class ReportStudentSummary(models.AbstractModel):
    _name = 'report.openeducat_attendance.student_summary_report_template'
    _description = 'Итоговый отчет успеваемости для печати'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['student.report.wizard'].browse(docids)
        year = wizard.academic_year_id
        
        # 1. Получаем все 4 четверти года
        terms = self.env['op.academic.term'].search([
            ('academic_year_id', '=', year.id),
            ('parent_term', '!=', False)
        ], order='term_start_date asc', limit=4)

        # 2. Определяем, какие классы мы печатаем
        if wizard.batch_ids:            
            batches = wizard.batch_ids.sorted('sequence')
        elif wizard.student_ids:
            batches = wizard.student_ids.mapped('course_detail_ids.batch_id').sorted('sequence')
        else:
            batches = self.env['op.batch'].search([], order='sequence')

        grouped_data = []

        for batch in batches:
            # Выбираем учеников для этого конкретного класса
            if wizard.student_ids:
                students_in_batch = wizard.student_ids.filtered(
                    lambda s: any(c.batch_id == batch for c in s.course_detail_ids)
                ).sorted('name')
            else:
                students_in_batch = self.env['op.student'].search([
                    ('course_detail_ids.batch_id', '=', batch.id)
                ], order='name')

            if not students_in_batch:
                continue

            # --- СУПЕР-ОПТИМИЗАЦИЯ: СКАЧИВАЕМ ДАННЫЕ ОДНИМ ЗАПРОСОМ НА ВЕСЬ КЛАСС ---
            # 1. Находим все карточки успеваемости для этого класса
            all_grades = self.env['op.subject.grades'].search([
                ('student_id', 'in', students_in_batch.ids),
                ('batch_id', '=', batch.id)
            ])

            # 2. Находим все строки посещаемости для этого класса за весь год
            all_attendance_lines = self.env['op.attendance.line'].search([
                ('student_id', 'in', students_in_batch.ids),
                ('term_id', 'in', terms.ids)
            ])

            student_list = []
            for student in students_in_batch:
                
                # Собираем оценки
                subject_data_list = [] # Переименовали для ясности
                # Добавим проверку, есть ли вообще предметы у курса
                subjects = batch.course_id.subject_ids or []
                
                for subject in subjects:
                    grade_rec = all_grades.filtered(
                        lambda g: g.student_id.id == student.id and g.subject_id.id == subject.id
                    )

                    # Берем первую запись, если их несколько (защита от дублей)
                    g = grade_rec[0] if grade_rec else False

                    subject_data_list.append({
                        'name': subject.name or 'Без названия',
                        'grades': [
                            (g.q1_final_grade or '') if g else '',
                            (g.q2_final_grade or '') if g else '',
                            (g.q3_final_grade or '') if g else '',
                            (g.q4_final_grade or '') if g else ''
                        ],
                        'year_grade': (g.final_quarter_grade or '') if g else ''
                    })

                # Собираем посещаемость (также фильтруем из памяти)
                y_total = {'missed': 0, 'sick': 0, 'late': 0}
                att_summary = []
                for term in terms:
                    t_lines = all_attendance_lines.filtered(
                        lambda l: l.student_id.id == student.id and l.term_id.id == term.id
                    )
                    m = len(t_lines.filtered(lambda l: l.absent))
                    s = len(t_lines.filtered(lambda l: l.excused))
                    l = len(t_lines.filtered(lambda l: l.late))
                    
                    att_summary.append({'total_missed': m + s, 'sick': s, 'late': l})
                    y_total['missed'] += (m + s)
                    y_total['sick'] += s
                    y_total['late'] += l

                student_list.append({
                    'student': student.name,
                    'subjects': subject_data_list,
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