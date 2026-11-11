import math

from odoo import api, fields, models


# Поля итоговых оценок ведомости по номеру четверти в учебном году.
FINAL_FIELDS = {
    1: 'q1_final_grade',
    2: 'q2_final_grade',
    3: 'q3_final_grade',
    4: 'q4_final_grade',
}

# Веса формулы СОУ (степень обученности, В.П. Беспалько).
SOU_WEIGHTS = {5: 1.0, 4: 0.64, 3: 0.36, 2: 0.14}


def _rint(value):
    """Математическое округление до целого (не banker's rounding)."""
    return int(math.floor(value + 0.5))


def _fmt(value):
    """Число с 2 знаками после запятой или «—»."""
    if value is None:
        return '—'
    return ('%.2f' % value).replace('.', ',')


def _label_lines(name):
    """Название предмета для вертикальной шапки: 1-2 сбалансированные
    строки. Возвращаю (строки, классы): у пары левая строка pa-l1
    (сдвиг вверх), правая pa-l2 (сдвиг вниз) — после поворота это
    соседние колонки вертикального текста, как в Дневник.ру."""
    words = name.split()
    if len(words) == 1:
        return [name], ['']
    total = sum(len(w_) for w_ in words)
    lines, cur, cur_len = [], [], 0
    for w_ in words:
        if cur and cur_len + len(w_) + 1 > total / 2 + 2:
            lines.append(' '.join(cur))
            cur, cur_len = [], 0
        cur.append(w_)
        cur_len += len(w_) + 1
    if cur:
        lines.append(' '.join(cur))
    lines = lines[:2]
    if len(lines) == 1:
        return lines, ['']
    return lines, ['pa-l1', 'pa-l2']


class ReportPerformanceAnalysis(models.AbstractModel):
    _name = 'report.openeducat_attendance.performance_analysis_template'
    _description = 'Сводная успеваемость классов (ученики x предметы)'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['performance.report.wizard'].browse(docids)
        grouped_data = []
        for batch in wizard.batch_ids or self._report_batches(wizard.academic_year_id):
            block = self._prepare_batch(batch, wizard)
            if block:
                grouped_data.append(block)
        return {
            'docs': wizard,
            'doc_ids': docids,
            'doc_model': 'performance.report.wizard',
            'grouped_data': grouped_data,
            'source_label': dict(
                wizard._fields['source'].selection).get(wizard.source),
        }

    def _report_batches(self, year):
        """Классы отчёта: выбранные или все классы года/всех годов."""
        if year:
            domain = [
                ('start_date', '<=', year.end_date),
                ('end_date', '>=', year.start_date),
            ]
        else:
            domain = []
        return self.env['op.batch'].sudo().search(domain, order='sequence')

    def _prepare_batch(self, batch, wizard):
        """Матрица одного класса: ученики x предметы + статистика.

        Целочисленная сетка (итоговые оценки / округлённые средние) — единый
        источник статистики: «Ср. балл», рейтинг, % кач., СОУ, группы. В
        режиме «Текущие средние» ячейка печатается с 2 знаками (точное
        среднее), но входит в расчёт округлённой — как в Дневник.ру.
        """
        today = fields.Date.context_today(self)
        source = wizard.source
        hide_empty = wizard.hide_empty_subjects

        # --- Учебный год и четверти периода ---
        # Батч живёт один год: год определяем по датам батча, у прошлогодних
        # классов будут свои четверти, у каждого класса — своя страница.
        year = self.env['op.academic.year'].search([
            ('start_date', '<=', batch.end_date),
            ('end_date', '>=', batch.start_date)], limit=1)
        if wizard.term_ids:
            terms = wizard.term_ids
        elif year:
            terms = self.env['op.academic.term'].search([
                ('academic_year_id', '=', year.id),
                ('parent_term', '!=', False)], order='term_start_date asc')
        else:
            terms = self.env['op.academic.term'].search([
                ('parent_term', '!=', False)], order='term_start_date asc')
        if not terms:
            return None

        # --- Ученики класса за год класса (правило «Итоговых оценок») ---
        course_domain = [('batch_id', '=', batch.id)]
        if year:
            course_domain.append(('academic_years_id', '=', year.id))
        courses = self.env['op.student.course'].sudo().search(course_domain)
        students = self.env['op.student'].search([
            ('id', 'in', courses.mapped('student_id').ids)], order='name')
        # Отчисленный (state='left') выпадает из отчёта только в незавершённом
        # году и только если он не числится running ни в одном классе года.
        if year and year.end_date >= today and students:
            left_ids = students.filtered(lambda s: s.state == 'left').ids
            if left_ids:
                running = self.env['op.student.course'].sudo().search_read([
                    ('student_id', 'in', left_ids),
                    ('academic_years_id', '=', year.id),
                    ('state', '=', 'running')], ['student_id'])
                running_ids = {r['student_id'][0] for r in running}
                students = students.filtered(
                    lambda s: s.state != 'left' or s.id in running_ids)
        if not students:
            return None

        # --- Ячейки: один поиск на класс, разбор в памяти ---
        cell_exact = {}  # (student_id, subject_id) -> значение ячейки
        subject_names = {}

        if source == 'final':
            # Итоговые: одна четверть -> её qN_final_grade, несколько ->
            # среднее итоговых выбранных четвертей.
            cards = self.env['op.subject.grades'].search([
                ('student_id', 'in', students.ids),
                ('batch_id', '=', batch.id)])
            term_index = {}
            if year:
                yterms = self.env['op.academic.term'].search([
                    ('academic_year_id', '=', year.id),
                    ('parent_term', '!=', False)], order='term_start_date asc')
                for idx, t in enumerate(yterms, 1):
                    term_index[t.id] = idx

            def _int_or_none(val):
                try:
                    return int(val) if val else None
                except (TypeError, ValueError):
                    return None

            for g in cards:
                subject_names.setdefault(g.subject_id.id, g.subject_id.name)
                vals = []
                for t in terms:
                    idx = term_index.get(t.id)
                    if not idx:
                        continue
                    v = _int_or_none(getattr(g, FINAL_FIELDS[idx], None))
                    if v is not None:
                        vals.append(v)
                if vals:
                    cell_exact[(g.student_id.id, g.subject_id.id)] = \
                        sum(vals) / len(vals)

        # Пропуски считаются за период независимо от источника ячеек;
        # в режиме «Текущие средние» те же строки отдают и оценки.
        att_lines = self.env['op.attendance.line'].search([
            ('student_id', 'in', students.ids),
            ('term_id', 'in', terms.ids),
            ('batch_id', '=', batch.id)])
        missed = {}
        marks = {}
        for l in att_lines:
            subject_names.setdefault(l.subject_id.id, l.subject_id.name)
            if l.absent or l.excused:
                missed[l.student_id.id] = missed.get(l.student_id.id, 0) + 1
            if source == 'current':
                hw = getattr(l, 'hw_sub_line_id', None)
                vals = [v for v in [
                    l.grade_1, l.grade_2,
                    hw.marks if hw else 0.0,
                    hw.marks_2 if hw else 0.0,
                ] if v and v > 0]
                if vals:
                    marks.setdefault((l.student_id.id, l.subject_id.id),
                                     []).extend(vals)
        if source == 'current':
            for pair, vals in marks.items():
                cell_exact[pair] = sum(vals) / len(vals)

        # --- Колонки: предметы курса + зачисления + карточки/журнал ---
        course_subjects = batch.course_id.subject_ids
        for s in course_subjects:
            subject_names.setdefault(s.id, s.name)
        for c in courses:
            for s in c.subject_ids:
                subject_names.setdefault(s.id, s.name)
        course_ids = course_subjects.ids
        # Предметы зачисления тоже становятся колонками, даже если оценок
        # по ним нет (при включённой галке пустые колонки скроются ниже).
        subject_ids = (set(course_ids)
                       | {s.id for c in courses for s in c.subject_ids}
                       | {sid for (_, sid) in cell_exact})

        def _subj_sort(sid):
            # Предметы курса — в порядке курса, остальные — по алфавиту
            # (английские А/Б и элективы рядом), как в «Итоговых оценках».
            if sid in course_ids:
                return (0, course_ids.index(sid), '')
            return (1, 0, subject_names.get(sid) or '')

        subject_ids = sorted(subject_ids, key=_subj_sort)

        # --- Строки учеников ---
        rows = []
        for st in students:
            # Короткое имя «Фамилия И.» — как в Дневник.ру и в мокапе;
            # полное имя не влезает в колонку матрицы.
            parts = st.name.split()
            display_name = st.name
            if len(parts) >= 2:
                display_name = parts[0] + ' ' + parts[1][0] + '.'
            cells_int, cells_exact_row = [], []
            for sid in subject_ids:
                val = cell_exact.get((st.id, sid))
                cells_exact_row.append(val)
                cells_int.append(_rint(val) if val is not None else None)
            filled = [c for c in cells_int if c is not None]
            avg = sum(filled) / len(filled) if filled else None
            if source == 'current':
                cell_strs = [_fmt(v) if v is not None else '—'
                             for v in cells_exact_row]
            else:
                cell_strs = [str(c) if c is not None else '—'
                             for c in cells_int]
            rows.append({
                'name': display_name,
                'cells': cells_int,
                'cell_strs': cell_strs,
                'avg': avg,
                'avg_str': _fmt(avg),
                'rank_str': '—',
                'missed': missed.get(st.id, 0),
            })

        # Рейтинг — соревновательный по «Ср. баллу» (равные баллы = один
        # номер, как в Дневник.ру).
        ranked = sorted([r for r in rows if r['avg'] is not None],
                        key=lambda r: -r['avg'])
        prev_avg, prev_rank = None, 0
        for i, r in enumerate(ranked, 1):
            if prev_avg is not None and abs(r['avg'] - prev_avg) < 1e-9:
                r['rank_str'] = str(prev_rank)
            else:
                r['rank_str'] = str(i)
                prev_rank = i
            prev_avg = r['avg']

        # --- Итоги по предметам (по целочисленной сетке) ---
        footer, hidden_cols = [], []
        for i, _sid in enumerate(subject_ids):
            vals = [r['cells'][i] for r in rows if r['cells'][i] is not None]
            if not vals:
                footer.append({'n': 0, 'avg_str': '—', 'kach_str': '—',
                               'sou_str': '—'})
                hidden_cols.append(i)
                continue
            n = len(vals)
            n5, n4, n3, n2 = (vals.count(m) for m in (5, 4, 3, 2))
            kach = (n5 + n4) / n * 100.0
            sou = (n5 * SOU_WEIGHTS[5] + n4 * SOU_WEIGHTS[4] +
                   n3 * SOU_WEIGHTS[3] + n2 * SOU_WEIGHTS[2]) / n * 100.0
            footer.append({
                'n': n,
                'avg': sum(vals) / n,
                'kach': kach,
                'sou': sou,
                'avg_str': _fmt(sum(vals) / n),
                'kach_str': _fmt(kach),
                'sou_str': _fmt(sou),
            })

        # Галка «Скрывать предметы без оценок»: колонки без единой оценки
        # уходят из таблицы целиком (согласовано 10.11.2026).
        if hide_empty and hidden_cols:
            keep = [i for i in range(len(subject_ids))
                    if i not in set(hidden_cols)]
            subject_ids = [subject_ids[i] for i in keep]
            footer = [footer[i] for i in keep]
            for r in rows:
                r['cells'] = [r['cells'][i] for i in keep]
                r['cell_strs'] = [r['cell_strs'][i] for i in keep]

        # Класс без единой оценки за период (галка «Скрывать пустые» убрала
        # все колонки) — страницы для него нет, как для классов без учеников.
        # Если пустым вышел весь отчёт, шаблон печатает «Нет данных».
        if not subject_ids:
            return None

        # --- Группы ---
        groups = self._classify(rows)

        # --- Сводка класса ---
        with_marks = [r for r in rows if r['avg'] is not None]
        subj_with = [f for f in footer if f['n']]
        summary = {
            'total': len(rows),
            'no_marks': len(groups['none']),
            'avg_str': _fmt(
                sum(r['avg'] for r in with_marks) / len(with_marks))
                if with_marks else '—',
            'kach_subj_str': _fmt(
                sum(f['kach'] for f in subj_with) / len(subj_with))
                if subj_with else '—',
            'sou_subj_str': _fmt(
                sum(f['sou'] for f in subj_with) / len(subj_with))
                if subj_with else '—',
            'usp_class_str': _fmt(
                (len(with_marks) - len(groups['neusp'])) / len(with_marks)
                * 100.0) if with_marks else '—',
            'kach_class_str': _fmt(
                (len(groups['otl']) + len(groups['hor'])) / len(with_marks)
                * 100.0) if with_marks else '—',
        }

        # Ширины колонок в pt (A4 landscape ~794pt контента): фиксированные
        # №/ФИО/Проп/Ср/Рей + равные доли на предметы. Один colgroup для
        # матрицы и таблицы статистики — колонки совпадают пиксель-в-пиксель.
        fixed_w = 20 + 100 + 26 + 30 + 26
        subj_w = (794 - fixed_w) // len(subject_ids)
        col_widths = [20, 100] + [subj_w] * len(subject_ids) + [26, 30, 26]

        return {
            'batch_name': batch.name,
            'year_name': year.name if year else '',
            'period_label': ', '.join(terms.mapped('name')),
            'subjects': [{'name': subject_names.get(sid) or 'Без названия',
                          'lines': list(zip(*_label_lines(subject_names.get(sid) or 'Без названия')))}
                         for sid in subject_ids],
            'col_widths': col_widths,
            'rows': rows,
            'footer': footer,
            'groups': groups,
            'summary': summary,
        }

    def _classify(self, rows):
        """Отличники/хорошисты/успевающие/неуспевающие с подгруппами
        «с одной "4"» / «с одной "3"» — по заполненным ячейкам сетки."""
        groups = {'otl': [], 'hor': [], 'hor_one4': [], 'usp': [],
                  'usp_one3': [], 'neusp': [], 'none': []}
        for r in rows:
            filled = [c for c in r['cells'] if c is not None]
            if not filled:
                groups['none'].append(r['name'])
            elif 2 in filled:
                groups['neusp'].append(r['name'])
            elif 3 in filled:
                groups['usp'].append(r['name'])
                if filled.count(3) == 1:
                    groups['usp_one3'].append(r['name'])
            elif all(c == 5 for c in filled):
                groups['otl'].append(r['name'])
            else:
                groups['hor'].append(r['name'])
                if filled.count(4) == 1:
                    groups['hor_one4'].append(r['name'])
        return groups
