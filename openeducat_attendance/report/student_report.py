from odoo import models, api, _
from odoo.exceptions import UserError

class ReportStudentSummary(models.AbstractModel):
    _name = 'report.openeducat_attendance.student_summary_report_template'
    _description = 'Итоговый отчет успеваемости для печати'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['student.report.wizard'].browse(docids)
        year = wizard.academic_year_id
        # Скрывать предметы без итоговых оценок (галка в визарде). По
        # умолчанию False: на первом этапе учителю видно, кто из
        # преподавателей ещё не проставил итоги.
        hide_empty = bool(wizard.hide_empty_subjects)
        
        # 1. Получаем все 4 четверти года
        terms = self.env['op.academic.term'].search([
            ('academic_year_id', '=', year.id),
            ('parent_term', '!=', False)
        ], order='term_start_date asc', limit=4)

        # 2. Классы выбранного учебного года. Батч живёт один год, в базе
        #    лежат и прошлогодние («5 А 2025/2026» и «5 А 2026/2027»), поэтому
        #    год — обязательный фильтр, а не только подпись в заголовке.
        year_batches = self.env['op.batch'].search([
            ('start_date', '<=', year.end_date),
            ('end_date', '>=', year.start_date),
        ], order='sequence')

        # 3. Определяем, какие классы мы печатаем
        if wizard.batch_ids:
            batches = (wizard.batch_ids & year_batches).sorted('sequence')
            if not batches:
                raise UserError(_(
                    'Выбранные классы не относятся к учебному году %s. '
                    'Выберите классы этого года.') % year.name)
        elif wizard.student_ids:
            batches = (
                wizard.student_ids.mapped('course_detail_ids.batch_id') & year_batches
            ).sorted('sequence')
            if not batches:
                raise UserError(_(
                    'Выбранные ученики не числятся в классах учебного года %s. '
                    'Выберите учеников этого года.') % year.name)
        else:
            batches = year_batches

        grouped_data = []

        for batch in batches:
            # Выбираем учеников этого класса за ВЫБРАННЫЙ год по записям
            # обучения (op.student.course): фильтр по academic_years_id.
            # Через домен по op.student это не сделать — два условия на одном
            # пути course_detail_ids применяются как два независимых EXISTS,
            # и ученик прошлого набора попадал бы в выборку.
            # sudo: read-ACL на op.student.course есть не у всех, кто открывает
            # визард; список учеников отчёта и так определяется ACL на
            # op.student ниже.
            courses = self.env['op.student.course'].sudo().search([
                ('batch_id', '=', batch.id),
                ('academic_years_id', '=', year.id),
            ])
            students_in_batch = self.env['op.student'].search([
                ('id', 'in', courses.mapped('student_id').ids),
            ], order='name')
            if wizard.student_ids:
                students_in_batch = students_in_batch & wizard.student_ids

            if not students_in_batch:
                continue

            # --- СУПЕР-ОПТИМИЗАЦИЯ: СКАЧИВАЕМ ДАННЫЕ ОДНИМ ЗАПРОСОМ НА ВЕСЬ КЛАСС ---
            # 1. Находим все карточки успеваемости для этого класса
            all_grades = self.env['op.subject.grades'].search([
                ('student_id', 'in', students_in_batch.ids),
                ('batch_id', '=', batch.id)
            ])

            # 2. Находим все строки посещаемости для этого класса за весь год
            #    (term — четверти выбранного года, batch — только свой класс:
            #    при переводе внутри года ученик числится в двух классах, и
            #    без фильтра по батчу посещаемость обоих попадала бы в
            #    каждый блок)
            all_attendance_lines = self.env['op.attendance.line'].search([
                ('student_id', 'in', students_in_batch.ids),
                ('term_id', 'in', terms.ids),
                ('batch_id', '=', batch.id),
            ])

            # Зачисления класса: из них берём индивидуальный набор
            # предметов ученика (английский А/Б, профильная математика —
            # того, чего в курсе класса нет вообще).
            enroll_by_student = {c.student_id.id: c for c in courses}

            # Имена предметов: из карточек и зачислений (одним проходом),
            # чтобы не дёргать ORM в цикле по ученикам.
            subject_names = {}
            for g in all_grades:
                subject_names[g.subject_id.id] = g.subject_id.name
            for c in courses:
                for sub in c.subject_ids:
                    subject_names.setdefault(sub.id, sub.name)

            student_list = []
            for student in students_in_batch:

                # Собираем оценки
                subject_data_list = []
                # Предметы отчёта = ЗАЧИСЛЕНИЕ ученика ∪ КАРТОЧКИ успеваемости.
                #
                # Зачисление (op.student.course.subject_ids) — индивидуальный
                # набор: в 6А английский разделён на «А»/«Б» (42/43), в 11А
                # трое профильников на профильной математике (39/40/41).
                # В курсе класса этих предметов нет, поэтому брать предметы
                # из курса было неверно — отчёт показывал пустую строку
                # «Английский язык» вместо «Английский А» с оценками.
                #
                # Карточки добавляют предметы, которых нет в зачислении:
                # элективные (21/22/27/28, 29) — они определяются позже,
                # к концу первой четверти, и в зачисление не попадают,
                # но уроки и оценки по ним уже есть.
                student_cards = all_grades.filtered(
                    lambda g: g.student_id.id == student.id
                )
                enrollment = enroll_by_student.get(student.id)
                enrolled_subject_ids = enrollment.subject_ids.ids if enrollment else []

                # Порядок: сначала предметы курса (как раньше), потом
                # остальные — по алфавиту, чтобы «Английский А»/«Б» и
                # элективные стояли рядом.
                course_subjects = batch.course_id.subject_ids
                course_ids = course_subjects.ids

                card_by_subject = {g.subject_id.id: g for g in student_cards}
                all_subject_ids = list(enrolled_subject_ids) + [
                    sid for sid in card_by_subject if sid not in enrolled_subject_ids
                ]

                def _subject_sort_key(sid, course_ids=course_ids,
                                      names=subject_names):
                    if sid in course_ids:
                        return (0, course_ids.index(sid), '')
                    return (1, 0, names.get(sid) or '')

                for sid in sorted(all_subject_ids, key=_subject_sort_key):
                    g = card_by_subject.get(sid)
                    grades = [
                        g.q1_final_grade or '' if g else '',
                        g.q2_final_grade or '' if g else '',
                        g.q3_final_grade or '' if g else '',
                        g.q4_final_grade or '' if g else '',
                    ]
                    year_grade = (g.final_quarter_grade or '') if g else ''
                    # Пустую строку по умолчанию НЕ прячем: по ней учитель
                    # видит, кто из преподавателей ещё не проставил итоги.
                    # Для финальной версии отчёта есть галка «скрывать
                    # предметы без оценок» — тогда пустые строки уходят.
                    if hide_empty and not any(grades) and not year_grade:
                        continue
                    subject_data_list.append({
                        'name': subject_names.get(sid) or 'Без названия',
                        'grades': grades,
                        'year_grade': year_grade,
                    })

                # Собираем посещаемость (также фильтруем из памяти)
                y_total = {'missed': 0, 'sick': 0, 'late': 0}
                att_summary = []
                for term in terms:
                    t_lines = all_attendance_lines.filtered(
                        lambda l: l.student_id.id == student.id and l.term_id.id == term.id
                    )                   
                    
                    m_count = len(t_lines.filtered(lambda l: l.absent or l.excused))                    
                    s_count = len(t_lines.filtered(lambda l: l.excused))
                    l_count = len(t_lines.filtered(lambda l: l.late))
                    
                    att_summary.append({
                        'total_missed': m_count, 
                        'sick': s_count, 
                        'late': l_count
                    })                    
                    
                    y_total['missed'] += m_count
                    y_total['sick'] += s_count
                    y_total['late'] += l_count

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