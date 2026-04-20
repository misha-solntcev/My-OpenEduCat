# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    # --- БАЗОВЫЕ ПОЛЯ ---
    student_id = fields.Many2one('op.student', 'Student', required=True, ondelete='cascade', index=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, ondelete='cascade', index=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    course_id = fields.Many2one('op.course', related='batch_id.course_id', store=True, readonly=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', compute='_compute_faculty_id', store=True)
    
    table_entries = fields.Text('Table Entries')
    marks = fields.Char('Marks Old'); behaviors = fields.Char('Behaviors Old')
    attendance_dates = fields.Text('Attendance Dates Old'); lesson_topics = fields.Text('Lesson Topics Old')
    
    student_avatar = fields.Image(related='student_id.image_128', string="Фото ученика")
    faculty_avatar = fields.Image(related='faculty_id.image_128', string="Фото учителя")
    textbook_image = fields.Image('Учебник', compute='_compute_textbook_image', store=True)
    student_name_short = fields.Char('Имя', compute='_compute_student_name_short', store=True)
    
    average_mark = fields.Float('Средняя', compute='_compute_all_stats', store=True)
    total_classes = fields.Integer('Всего', compute='_compute_all_stats', store=True)
    present_classes = fields.Integer('Посещено', compute='_compute_all_stats', store=True)
    last_attendance_date = fields.Date('Последний урок', compute='_compute_all_stats', store=True)
    attendance_rate = fields.Float('Посещаемость %', compute='_compute_all_stats', store=True)

    # --- ЧЕТВЕРТИ (STORED) ---
    q1_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q1_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q1_average_mark = fields.Float(compute='_compute_all_stats', store=True); q1_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q1_count_5 = fields.Integer(compute='_compute_all_stats', store=True); q1_count_4 = fields.Integer(compute='_compute_all_stats', store=True)
    q1_count_3 = fields.Integer(compute='_compute_all_stats', store=True); q1_count_2 = fields.Integer(compute='_compute_all_stats', store=True)

    q2_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q2_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q2_average_mark = fields.Float(compute='_compute_all_stats', store=True); q2_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q2_count_5 = fields.Integer(compute='_compute_all_stats', store=True); q2_count_4 = fields.Integer(compute='_compute_all_stats', store=True)
    q2_count_3 = fields.Integer(compute='_compute_all_stats', store=True); q2_count_2 = fields.Integer(compute='_compute_all_stats', store=True)

    q3_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q3_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q3_average_mark = fields.Float(compute='_compute_all_stats', store=True); q3_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q3_count_5 = fields.Integer(compute='_compute_all_stats', store=True); q3_count_4 = fields.Integer(compute='_compute_all_stats', store=True)
    q3_count_3 = fields.Integer(compute='_compute_all_stats', store=True); q3_count_2 = fields.Integer(compute='_compute_all_stats', store=True)

    q4_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q4_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q4_average_mark = fields.Float(compute='_compute_all_stats', store=True); q4_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q4_count_5 = fields.Integer(compute='_compute_all_stats', store=True); q4_count_4 = fields.Integer(compute='_compute_all_stats', store=True)
    q4_count_3 = fields.Integer(compute='_compute_all_stats', store=True); q4_count_2 = fields.Integer(compute='_compute_all_stats', store=True)

    attendance_bar_html = fields.Html(compute='_compute_visuals', sanitize=False)
    year_progress_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    attendance_donut_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    grades_histogram_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q1_attendance_stats_html = fields.Html(compute='_compute_visuals', sanitize=False)
    q2_attendance_stats_html = fields.Html(compute='_compute_visuals', sanitize=False)
    q3_attendance_stats_html = fields.Html(compute='_compute_visuals', sanitize=False)
    q4_attendance_stats_html = fields.Html(compute='_compute_visuals', sanitize=False)

    q1_final_grade = fields.Char('Итог Q1'); q2_final_grade = fields.Char('Итог Q2')
    q3_final_grade = fields.Char('Итог Q3'); q4_final_grade = fields.Char('Итог Q4')
    final_quarter_grade = fields.Char('Годовая')

    # --- ОПТИМИЗИРОВАННЫЙ СБОР СТРОК ---
    @api.depends('student_id', 'subject_id')
    def _compute_line_ids(self):
        """ 
        Метод с использованием точных дат четвертей из настроек Odoo.
        Привязывает оценки к вкладкам Q1-Q4 строго по календарю.
        """
        if self.env.context.get('skip_compute'): return
        
        all_student_ids = self.mapped('student_id').ids
        all_subject_ids = self.mapped('subject_id').ids
        if not all_student_ids: return

        # 1. Получаем все оценки для пачки учеников
        lines = self.env['op.attendance.line'].sudo().search([
            ('student_id', 'in', all_student_ids),
            ('subject_id', 'in', all_subject_ids)
        ])

        # 2. Получаем все четверти из настроек (те, у которых есть "Полугодие" / parent_term)
        terms_db = self.env['op.academic.term'].sudo().search([('parent_term', '!=', False)])
        
        # Создаем карту дат: {1: (start, end), 2: (start, end)...}
        quarter_dates = {}
        for i in range(1, 5):
            # Ищем четверть, в названии которой есть цифра 1, 2, 3 или 4
            term = terms_db.filtered(lambda t: str(i) in (t.name or ''))
            if term:
                quarter_dates[i] = (term[0].term_start_date, term[0].term_end_date)

        # 3. Группируем строки по (студент, предмет) для скорости
        line_map = {}
        for l in lines:
            key = (l.student_id.id, l.subject_id.id)
            if key not in line_map: line_map[key] = []
            line_map[key].append(l)

        # 4. Распределяем строки по карточкам успеваемости
        for rec in self:
            my_lines = line_map.get((rec.student_id.id, rec.subject_id.id), [])
            for i in range(1, 5):
                dates = quarter_dates.get(i)
                if dates and my_lines:
                    start, end = dates
                    # Фильтруем: дата урока должна быть строго ВНУТРИ дат четверти
                    q_ids = [l.id for l in my_lines if l.attendance_date and start <= l.attendance_date <= end]
                    setattr(rec, f'q{i}_line_ids', [(6, 0, q_ids)])
                else:
                    setattr(rec, f'q{i}_line_ids', [(6, 0, [])])

    # --- РАСЧЕТ ВСЕЙ СТАТИСТИКИ ---
    @api.depends(
        'q1_line_ids.grade_1', 'q1_line_ids.grade_2', 'q1_line_ids.grade_3', 'q1_line_ids.present',
        'q2_line_ids.grade_1', 'q2_line_ids.grade_2', 'q2_line_ids.grade_3', 'q2_line_ids.present',
        'q3_line_ids.grade_1', 'q3_line_ids.grade_2', 'q3_line_ids.grade_3', 'q3_line_ids.present',
        'q4_line_ids.grade_1', 'q4_line_ids.grade_2', 'q4_line_ids.grade_3', 'q4_line_ids.present'
    )
    def _compute_all_stats(self):
        if self.env.context.get('skip_compute'): return
        line_obj = self.env['op.attendance.line']
        for rec in self:
            all_l = rec.q1_line_ids | rec.q2_line_ids | rec.q3_line_ids | rec.q4_line_ids
            f = line_obj.get_stats_from_lines(all_l)
            rec.update({'average_mark': f['avg'], 'total_classes': f['total'], 'present_classes': f['present'], 'attendance_rate': f['rate'], 'last_attendance_date': f['last_date']})
            for i in range(1, 5):
                qs = line_obj.get_stats_from_lines(getattr(rec, f'q{i}_line_ids'))
                rec.update({f'q{i}_average_mark': qs['avg'], f'q{i}_last_remark': qs['last_remark'], f'q{i}_count_5': qs['counts'][5], f'q{i}_count_4': qs['counts'][4], f'q{i}_count_3': qs['counts'][3], f'q{i}_count_2': qs['counts'][2]})

    # --- МИГРАЦИЯ (ЖЕСТКАЯ ЛОГИКА) ---
    def action_migrate_old_data(self):
        """ 
        Турбо-мигратор с подавлением всех расчетов Odoo.
        """
        import re
        from datetime import datetime
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        
        recs = self.sudo().search([('table_entries', '!=', False)])
        total = len(recs)
        _logger.info(f">>> СТАРТ ТУРБО-МИГРАЦИИ: {total} записей.")

        present_type = self.env['op.attendance.type'].sudo().search([('present', '=', True)], limit=1)
        
        # 1. Загружаем все данные в кэш один раз
        all_lines = self.env['op.attendance.line'].sudo().search([
            ('student_id', 'in', recs.mapped('student_id').ids),
            ('subject_id', 'in', recs.mapped('subject_id').ids)
        ])
        line_cache = {(l.student_id.id, l.subject_id.id, str(l.attendance_date)): l for l in all_lines}

        all_sheets = self.env['op.attendance.sheet'].sudo().search([
            ('subject_id', 'in', recs.mapped('subject_id').ids),
            ('batch_id', 'in', recs.mapped('batch_id').ids)
        ])
        sheet_cache = {(str(s.attendance_date), s.subject_id.id, s.batch_id.id): s.id for s in all_sheets}

        # 2. Обработка порциями (batch)
        chunk_size = 50
        for i in range(0, total, chunk_size):
            chunk = recs[i:i + chunk_size]
            
            # Отключаем ВСЕ вычисления и трекинг внутри пачки
            for record in chunk.with_context(skip_compute=True, tracking_disable=True, mail_notrack=True, no_recompute=True):
                entries = record.table_entries.split(', ')
                for entry in entries:
                    parts = [p.strip() for p in entry.split('|')]
                    if not parts or not date_pattern.match(parts[0]): continue
                    
                    date_str = parts[0]
                    vals = {}
                    if len(parts) > 1 and parts[1] and parts[1][0].isdigit(): vals['grade_1'] = float(parts[1][0])
                    if len(parts) > 2 and parts[2] and parts[2][0].isdigit(): vals['grade_2'] = float(parts[2][0])
                    if len(parts) > 8 and parts[8]: vals['remark'] = parts[8]
                    if '✓' in entry and present_type: vals['attendance_type_id'] = present_type.id
                    
                    if not vals: continue

                    line = line_cache.get((record.student_id.id, record.subject_id.id, date_str))
                    if line:
                        line.write(vals)
                    else:
                        sheet_id = sheet_cache.get((date_str, record.subject_id.id, record.batch_id.id))
                        if sheet_id:
                            cv = {'attendance_id': sheet_id, 'student_id': record.student_id.id}
                            cv.update(vals)
                            self.env['op.attendance.line'].create(cv)

            self.env.cr.commit()
            _logger.info(f"--- Мигрировано {min(i + chunk_size, total)} из {total}")

        _logger.info(">>> ВСЁ! Нажмите 'Обновить статистику' для отрисовки.")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Готово', 'message': 'Оценки перенесены. Запустите пересчет.', 'type': 'success'}}

    def action_force_recompute(self):
        all_recs = self if self else self.search([])
        total = len(all_recs)
        batch_size = 50
        for i in range(0, total, batch_size):
            batch = all_recs[i:i + batch_size]
            batch.invalidate_recordset()
            batch._compute_line_ids()
            batch._compute_all_stats()
            self.env.cr.commit()
            _logger.info(f"--- Статистика: {i + len(batch)} из {total}")
        return True

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ (Без изменений) ---
    @api.depends('attendance_rate', 'q1_line_ids', 'q2_line_ids', 'q3_line_ids', 'q4_line_ids')
    def _compute_visuals(self):
        if self.env.context.get('skip_compute'): return
        line_obj = self.env['op.attendance.line']
        for rec in self:
            # 1. Сбор всех строк для расчетов
            all_l = rec.q1_line_ids | rec.q2_line_ids | rec.q3_line_ids | rec.q4_line_ids
            stats = line_obj.get_stats_from_lines(all_l)
            
            # 2. Обновление текстовых сводок по четвертям (бейджи снизу)
            for i in range(1, 5):
                q_stats = line_obj.get_stats_from_lines(getattr(rec, f'q{i}_line_ids'))
                setattr(rec, f'q{i}_attendance_stats_html', q_stats['html_summary'])
            
            # 3. Генератор линейного графика (уже был)
            rec.year_progress_svg = self._generate_svg_graph(rec)
            
            # 4. Генератор круговой диаграммы (новый)
            rec.attendance_donut_svg = self._generate_attendance_donut(rec)

            # Гистограмма оценок
            rec.grades_histogram_svg = self._generate_grades_histogram(stats)
            
            # 5. Старый прогресс-бар (оставим для совместимости)
            r = rec.attendance_rate
            c = 'bg-success' if r >= 80 else 'bg-warning' if r >= 60 else 'bg-danger'
            rec.attendance_bar_html = f'<div class="progress" style="height:10px; background:#eee;"><div class="progress-bar {c}" style="width:{r}%"></div></div>'

    def _generate_svg_graph(self, rec):
        """ 
        Восстановленный график с метками оценок (5, 4, 3, 2) и сеткой 
        """
        avgs = [rec.q1_average_mark, rec.q2_average_mark, rec.q3_average_mark, rec.q4_average_mark]
        w, h = 400, 160
        # Сдвигаем точки вправо (px[0]=45), чтобы освободить место под цифры слева
        px = [45, 153, 261, 370]
        
        # 1. Генерируем сетку (линии и цифры)
        # Координаты Y для оценок: 5 -> 30, 4 -> 66, 3 -> 103, 2 -> 140
        grid = """
            <text x="5" y="35" font-family="sans-serif" font-size="22" fill="#adb5bd" font-weight="bold">5</text>
            <line x1="40" y1="30" x2="400" y2="30" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
            
            <text x="5" y="71" font-family="sans-serif" font-size="22" fill="#adb5bd" font-weight="bold">4</text>
            <line x1="40" y1="66" x2="400" y2="66" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
            
            <text x="5" y="108" font-family="sans-serif" font-size="22" fill="#adb5bd" font-weight="bold">3</text>
            <line x1="40" y1="103" x2="400" y2="103" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
            
            <text x="5" y="145" font-family="sans-serif" font-size="22" fill="#adb5bd" font-weight="bold">2</text>
            <line x1="40" y1="140" x2="400" y2="140" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
        """

        coords = []
        dots = []
        for i, val in enumerate(avgs):
            x = px[i]
            if val > 0:
                # Масштабируем Y: оценка 2.0 это низ (140), 5.0 это верх (30)
                y = 140 - ((val - 2) * 36.6)
                coords.append((x, y))
                # Белая точка с жирной фиолетовой обводкой
                dots.append(f'<circle cx="{x}" cy="{y}" r="7" fill="white" stroke="#714B67" stroke-width="5"/>')
            else:
                # Серая точка-плейсхолдер для будущих четвертей
                dots.append(f'<circle cx="{x}" cy="85" r="5" fill="#f0f0f0" stroke="#ccc" stroke-width="2"/>')

        path_html = ""
        if len(coords) >= 2:
            d = f"M {coords[0][0]} {coords[0][1]}"
            for i in range(1, len(coords)):
                d += f" L {coords[i][0]} {coords[i][1]}"
            
            # Добавляем полупрозрачную заливку под графиком
            grad_id = f"grad_dyn_{rec.id}"
            path_html = f"""
                <defs>
                    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#714B67; stop-opacity:0.2" />
                        <stop offset="100%" style="stop-color:#714B67; stop-opacity:0" />
                    </linearGradient>
                </defs>
                <path d="{d} L {coords[-1][0]} {h} L {coords[0][0]} {h} Z" fill="url(#{grad_id})" />
                <path d="{d}" fill="none" stroke="#714B67" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
            """
        
        return f'<svg viewBox="0 0 400 160" preserveAspectRatio="xMidYMid meet" style="width:100%; height:100px; display:block;">{grid}{path_html}{"".join(dots)}</svg>'

    def _generate_attendance_donut(self, rec):
        """ Генерирует сплошную круговую диаграмму (Pie Chart) с компактной легендой """
        line_obj = self.env['op.attendance.line']
        stats = line_obj.get_stats_from_lines(rec.q1_line_ids | rec.q2_line_ids | rec.q3_line_ids | rec.q4_line_ids)
        total = stats['total']
        if total == 0: return '<div class="text-muted small text-center py-3">Нет данных</div>'

        # Цветовая карта (названия должны совпадать с БД)
        color_map = {
            'Присутствует': '#28a745', 'Дистанционно': '#a5d6a7', 'Опоздал': '#ffc107',
            'Болеет': '#9c27b0', 'Уважительная причина': '#17a2b8', 'Прогул': '#dc3545',
        }
        # Очистка ключей от возможных пробелов
        detailed = {k.strip(): v for k, v in stats.get('types_detailed', {}).items()}
        
        segments = []
        current_offset = 0
        legend_html = ""

        for label, color in color_map.items():
            count = detailed.get(label, 0)
            if count > 0:
                percent = (count / total) * 100
                # stroke-width="31.8" делает круг полностью закрашенным (без дырки)
                segments.append(f"""
                    <circle cx="21" cy="21" r="15.915" fill="transparent" 
                            stroke="{color}" stroke-width="31.8" 
                            stroke-dasharray="{percent} {100-percent}" 
                            stroke-dashoffset="-{current_offset}"></circle>
                """)
                current_offset += percent
                # Добавляем в легенду только если count > 0
                legend_html += f"""
                    <div class="col-6 d-flex align-items-center mb-1" style="font-size: 0.7rem; line-height: 1.1;">
                        <span style="width:8px; height:8px; background:{color}; border-radius:2px; flex-shrink:0;" class="me-1"></span>
                        <span class="text-truncate" title="{label}">{label}: <b>{count}</b></span>
                    </div>"""

        return f"""
        <div class="w-100">
            <div class="d-flex align-items-center justify-content-center mb-2">
                <svg width="80" height="80" viewBox="0 0 42 42" style="transform: rotate(-90deg); border-radius: 50%;">
                    <circle cx="21" cy="21" r="15.915" fill="#f8f9fa"></circle>
                    {"".join(segments)}
                </svg>
            </div>
            <div class="row g-0 border-top pt-2">{legend_html}</div>
        </div>"""

    def _generate_grades_histogram(self, stats):
        """ Генерирует гистограмму оценок с правильными отступами для цифр """
        counts = stats['counts']
        max_count = max(counts.values()) or 1
        colors = {5: "#28a745", 4: "#007bff", 3: "#ffc107", 2: "#dc3545"}
        labels = {5: "5", 4: "4", 3: "3", 2: "2"}
        
        top_margin = 20    # Запас места сверху для цифр
        bar_area_h = 50    
        bottom_margin = 20 
        
        svg_width = 130
        svg_total_height = top_margin + bar_area_h + bottom_margin
        bar_width = 20
        gap = 8
        bars_html = ""

        for i, grade in enumerate([5, 4, 3, 2]):
            val = counts[grade]
            h = (val / max_count) * bar_area_h
            x = i * (bar_width + gap) + 15
            y_bar_top = top_margin + (bar_area_h - h)
            
            bars_html += f"""
                <rect x="{x}" y="{y_bar_top}" width="{bar_width}" height="{h}" fill="{colors[grade]}" rx="3"></rect>
                <text x="{x + bar_width/2}" y="{y_bar_top - 5}" text-anchor="middle" font-size="11" fill="#333" font-weight="bold">
                    {val if val > 0 else ''}
                </text>
                <text x="{x + bar_width/2}" y="{top_margin + bar_area_h + 15}" text-anchor="middle" font-size="10" fill="#999">
                    {labels[grade]}
                </text>
            """
        return f'<div class="d-flex flex-column align-items-center justify-content-center w-100"><svg width="{svg_width}" height="{svg_total_height}" viewBox="0 0 {svg_width} {svg_total_height}">{bars_html}</svg></div>'

    @api.depends('subject_id', 'batch_id')
    def _compute_faculty_id(self):
        for r in self:
            s = self.env['op.session'].search([('subject_id', '=', r.subject_id.id), ('batch_id', '=', r.batch_id.id)], limit=1)
            r.faculty_id = s.faculty_id.id if s else False

    @api.depends('subject_id', 'batch_id')
    def _compute_textbook_image(self):
        for r in self:        
            m = self.env['op.media'].search([
                ('subject_ids', 'in', r.subject_id.ids),
                ('course_ids', 'in', r.batch_id.course_id.ids)
            ], limit=1)        
            
            if not m:
                m = self.env['op.media'].search([('subject_ids', 'in', r.subject_id.ids)], limit=1)
                
            r.textbook_image = m.x_image_128 if m else False


    @api.depends('student_id')
    def _compute_student_name_short(self):
        for r in self: r.student_name_short = (f"{r.student_id.first_name or ''} {r.student_id.last_name or ''}").strip()

