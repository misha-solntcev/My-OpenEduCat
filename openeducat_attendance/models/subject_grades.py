# -*- coding: utf-8 -*-
import logging
import re
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
    student_avatar = fields.Image(related='student_id.image_128', string="Фото ученика")
    faculty_avatar = fields.Image(related='faculty_id.image_128', string="Фото учителя")
    textbook_image = fields.Image('Учебник', compute='_compute_textbook_image', store=True)
    student_name_short = fields.Char('Имя', compute='_compute_student_name_short', store=True)
    
    average_mark = fields.Float('Средняя', compute='_compute_all_stats', store=True)
    attendance_rate = fields.Float('Посещаемость %', compute='_compute_all_stats', store=True)
    total_classes = fields.Integer(compute='_compute_all_stats', store=True)
    present_classes = fields.Integer(compute='_compute_all_stats', store=True)

    # --- ЧЕТВЕРТИ (ДАННЫЕ) ---
    q1_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q1_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q1_average_mark = fields.Float(compute='_compute_all_stats', store=True)
    q1_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q1_final_grade = fields.Char('Итог Q1')

    q2_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q2_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q2_average_mark = fields.Float(compute='_compute_all_stats', store=True)
    q2_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q2_final_grade = fields.Char('Итог Q2')

    q3_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q3_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q3_average_mark = fields.Float(compute='_compute_all_stats', store=True)
    q3_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q3_final_grade = fields.Char('Итог Q3')

    q4_line_ids = fields.Many2many('op.attendance.line', 'rel_grades_q4_lines', 'grade_id', 'line_id', compute='_compute_line_ids', store=True)
    q4_average_mark = fields.Float(compute='_compute_all_stats', store=True)
    q4_last_remark = fields.Char(compute='_compute_all_stats', store=True)
    q4_final_grade = fields.Char('Итог Q4')

    # --- ВИЗУАЛИЗАЦИЯ (SVG/HTML) ---
    year_progress_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    attendance_donut_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    grades_histogram_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    final_quarter_grade = fields.Char('Годовая')

    # Поля для графиков по четвертям
    q1_attendance_donut_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q1_grades_histogram_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q2_attendance_donut_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q2_grades_histogram_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q3_attendance_donut_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q3_grades_histogram_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q4_attendance_donut_svg = fields.Html(compute='_compute_visuals', sanitize=False)
    q4_grades_histogram_svg = fields.Html(compute='_compute_visuals', sanitize=False)

    @api.depends('student_id', 'subject_id')
    def _compute_line_ids(self):
        if self.env.context.get('skip_compute'): return
        terms = self.env['op.academic.term'].sudo().search([('parent_term', '!=', False)])
        q_dates = {}
        for i in range(1, 5):
            t = terms.filtered(lambda x: str(i) in (x.name or ''))
            if t: q_dates[i] = (t[0].term_start_date, t[0].term_end_date)
        for rec in self:
            lines = self.env['op.attendance.line'].sudo().search([('student_id', '=', rec.student_id.id), ('subject_id', '=', rec.subject_id.id)])
            for i in range(1, 5):
                d = q_dates.get(i)
                if d and lines:
                    ids = lines.filtered(lambda l: l.attendance_date and d[0] <= l.attendance_date <= d[1]).ids
                    setattr(rec, f'q{i}_line_ids', [(6, 0, ids)])
                else:
                    setattr(rec, f'q{i}_line_ids', [(6, 0, [])])

    @api.depends('q1_line_ids', 'q2_line_ids', 'q3_line_ids', 'q4_line_ids')
    def _compute_all_stats(self):
        l_obj = self.env['op.attendance.line']
        for rec in self:
            all_l = rec.q1_line_ids | rec.q2_line_ids | rec.q3_line_ids | rec.q4_line_ids
            res = l_obj.get_stats_from_lines(all_l)
            rec.update({'average_mark': res['avg'], 'attendance_rate': res['rate'], 'total_classes': res['total'], 'present_classes': res['present']})
            for i in range(1, 5):
                q_res = l_obj.get_stats_from_lines(getattr(rec, f'q{i}_line_ids'))
                rec.update({f'q{i}_average_mark': q_res['avg'], f'q{i}_last_remark': q_res['last_remark']})

    @api.depends('average_mark', 'attendance_rate', 'q1_line_ids', 'q2_line_ids', 'q3_line_ids', 'q4_line_ids')
    def _compute_visuals(self):
        l_obj = self.env['op.attendance.line']
        for rec in self:
            year_stats = l_obj.get_stats_from_lines(rec.q1_line_ids | rec.q2_line_ids | rec.q3_line_ids | rec.q4_line_ids)
            rec.year_progress_svg = self._generate_svg_graph(rec)
            rec.attendance_donut_svg = self._generate_attendance_donut(year_stats)
            rec.grades_histogram_svg = self._generate_grades_histogram(year_stats)
            for i in range(1, 5):
                q_stats = l_obj.get_stats_from_lines(getattr(rec, f'q{i}_line_ids'))
                setattr(rec, f'q{i}_attendance_donut_svg', self._generate_attendance_donut(q_stats))
                setattr(rec, f'q{i}_grades_histogram_svg', self._generate_grades_histogram(q_stats))

    @api.depends('subject_id', 'course_id')
    def _compute_textbook_image(self):
        for r in self:
            domain = [('subject_ids', 'in', r.subject_id.ids)]
            media = self.env['op.media'].sudo().search(domain + [('course_ids', 'in', r.course_id.ids)], limit=1)
            if not media:
                media = self.env['op.media'].sudo().search(domain, limit=1)
            r.textbook_image = media.x_image_128 if media else False

    def action_migrate_old_data(self):
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        recs = self.sudo().search([('table_entries', '!=', False)])
        present_type = self.env['op.attendance.type'].sudo().search([('present', '=', True)], limit=1)
        for record in recs.with_context(skip_compute=True):
            for entry in record.table_entries.split(', '):
                parts = [p.strip() for p in entry.split('|')]
                if not parts or not date_pattern.match(parts[0]): continue
                vals = {}
                if len(parts) > 1 and parts[1] and parts[1][0].isdigit(): vals['grade_1'] = float(parts[1][0])
                if len(parts) > 2 and parts[2] and parts[2][0].isdigit(): vals['grade_2'] = float(parts[2][0])
                if len(parts) > 8 and parts[8]: vals['remark'] = parts[8]
                if '✓' in entry and present_type: vals['attendance_type_id'] = present_type.id
                line = self.env['op.attendance.line'].sudo().search([('student_id', '=', record.student_id.id), ('subject_id', '=', record.subject_id.id), ('attendance_date', '=', parts[0])], limit=1)
                if line: line.write(vals)
        return True

    def action_force_recompute(self):
        self._compute_line_ids()
        self._compute_all_stats()
        return True

    # Круговая диаграмма посещаемости с легендой
    def _generate_attendance_donut(self, stats):
        total = stats['total']
        if total == 0: 
            return '<div class="text-muted small py-4 text-center">Нет данных</div>'
        
        detailed = stats.get('types_detailed', {})
        segments, offset, legend = [], 0, ""

        # Цвета посещаемости (прописываем здесь, так как constants.py не внедрен)
        attendance_colors = {
            'Присутствует': '#28a745', 
            'Дистанционно': '#a5d6a7', 
            'Опоздал': '#ffc107', 
            'Болеет': '#9c27b0', 
            'Уважительная причина': '#17a2b8', 
            'Прогул': '#dc3545',
            'default': '#dee2e6'
        }

        # CSS Стили для анимации вращения и заполнения
        styles = """
        <style>
            @keyframes donut-show {
                from { stroke-dasharray: 0 100; }
            }
            .donut-seg {
                animation: donut-show 1.2s ease-in-out forwards;
            }
        </style>
        """

        for label, count in detailed.items():
            color = attendance_colors.get(label.strip(), attendance_colors['default'])
            pct = (count / total) * 100
            
            # r=15.915 делает длину окружности ровно 100
            segments.append(f"""
                <circle class="donut-seg" cx="21" cy="21" r="15.915" fill="none" 
                        stroke="{color}" stroke-width="31.8" 
                        stroke-dasharray="{pct} {100-pct}" 
                        stroke-dashoffset="-{offset}"/>
            """)
            offset += pct
            legend += f"""
                <div class="d-flex align-items-center mb-1" style="font-size:10px; line-height: 1;">
                    <span style="width:7px; height:7px; background:{color}; border-radius:50%; flex-shrink:0;" class="me-1"></span>
                    <span class="text-truncate">{label}: <b>{count}</b></span>
                </div>"""

        return f"""
            <div class="row g-0 align-items-center h-100">
                <div class="col-5 d-flex align-items-center justify-content-center">
                    <svg viewBox="0 0 42 42" style="width: 80px; height: 80px; transform: rotate(-90deg); border-radius: 50%;">
                        {styles}
                        <circle cx="21" cy="21" r="15.915" fill="#f8f9fa"/>
                        {"".join(segments)}
                    </svg>
                </div>
                <div class="col-7 ps-2 text-start">
                    {legend}
                </div>
            </div>
        """
    # Столбчатая диаграмма распределения оценок
    def _generate_grades_histogram(self, stats):
        counts = stats['counts']
        if not any(counts.values()): return '<div class="text-muted small py-4 text-center">Нет оценок</div>'
        max_v = max(counts.values()) or 1
        
        colors = {
            5: "#714B67", 4: "#00A09D", 3: "#E9C46A", 2: "#E46F78"
        }

        # Блок стилей для анимации
        # .bar-rect — анимирует рост столбика
        # .bar-text — плавно проявляет цифры после того, как столбик вырос
        styles = """
        <style>
            @keyframes grow-bar {
                from { transform: scaleY(0); }
                to { transform: scaleY(1); }
            }
            @keyframes fade-text {
                from { opacity: 0; transform: translateY(5px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .bar-rect {
                transform-origin: 0 72px; /* Фиксируем низ столбика на базовой линии */
                animation: grow-bar 0.7s cubic-bezier(0.17, 0.67, 0.83, 0.67) forwards;
            }
            .bar-text {
                opacity: 0;
                animation: fade-text 0.5s ease-out forwards;
            }
        </style>
        """
        
        bars = styles
        for i, g in enumerate([5, 4, 3, 2]):
            val = counts[g]
            h = (val / max_v) * 50
            x = i * 32 + 20
            y = 20 + (50 - h)
            
            # Добавляем класс bar-rect и задержку анимации (animation-delay)
            # чтобы столбики росли по очереди (эффект волны)
            bars += f"""
                <rect class="bar-rect" x="{x}" y="{y}" width="22" height="{h}" 
                      fill="{colors[g]}" rx="3" 
                      style="animation-delay: {i*0.1}s;"/>
            """
            
            # Текст над столбиком (количество) с задержкой, чтобы он появился в конце
            if val > 0:
                bars += f"""
                    <text class="bar-text" x="{x+11}" y="{y-5}" 
                          text-anchor="middle" font-size="11" font-weight="bold" 
                          fill="{colors[g]}" style="animation-delay: {0.5 + i*0.1}s;">
                        {val}
                    </text>
                """
            
            # Подпись снизу (оценка)
            bars += f'<text x="{x+11}" y="90" text-anchor="middle" font-size="11" fill="#999" font-weight="bold">{g}</text>'
            
            # Базовая линия
            bars += f'<line x1="{x}" y1="72" x2="{x+22}" y2="72" stroke="{colors[g]}" stroke-width="2" opacity="0.6"/>'
        
        return f'<div class="text-center"><svg width="150" height="90">{bars}</svg></div>'

    # График динамики с градиентной заливкой под линией
    def _generate_svg_graph(self, rec):        
        avgs = [rec.q1_average_mark, rec.q2_average_mark, rec.q3_average_mark, rec.q4_average_mark]
        h = 160  # Высота SVG
        px = [45, 153, 261, 370]
        
        # Сетка и подписи
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

        coords, dots = [], []
        for i, val in enumerate(avgs):
            x = px[i]
            if val > 0:
                y = 140 - ((val - 2) * 36.6)
                coords.append((x, y))
                dots.append(f'<circle cx="{x}" cy="{y}" r="8" fill="white" stroke="#714B67" stroke-width="6"/>')
            else:
                dots.append(f'<circle cx="{x}" cy="85" r="5" fill="#f8f9fa" stroke="#e0e0e0" stroke-width="2"/>')

        path_elements = ""
        if len(coords) >= 2:
            # Строим основную линию
            d_line = f"M {coords[0][0]} {coords[0][1]}"
            for i in range(1, len(coords)):
                d_line += f" L {coords[i][0]} {coords[i][1]}"
            
            # Строим замкнутый контур для градиента (линия -> низ -> начало)
            d_fill = f"{d_line} L {coords[-1][0]} {h} L {coords[0][0]} {h} Z"
            
            grad_id = f"grad_dyn_{rec.id}"
            path_elements = f"""
                <defs>
                    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#714B67; stop-opacity:0.25" />
                        <stop offset="100%" style="stop-color:#714B67; stop-opacity:0" />
                    </linearGradient>
                </defs>
                <path d="{d_fill}" fill="url(#{grad_id})" />
                <path d="{d_line}" fill="none" stroke="#714B67" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
            """
        
        return f'<svg viewBox="0 0 400 160" preserveAspectRatio="xMidYMid meet" style="width:100%; height:100px;">{grid}{path_elements}{"".join(dots)}</svg>'

    @api.depends('subject_id', 'batch_id')
    def _compute_faculty_id(self):
        for r in self:
            s = self.env['op.session'].search([('subject_id', '=', r.subject_id.id), ('batch_id', '=', r.batch_id.id)], limit=1)
            r.faculty_id = s.faculty_id.id if s else False

    @api.depends('student_id')
    def _compute_student_name_short(self):
        for r in self: r.student_name_short = f"{r.student_id.first_name or ''} {r.student_id.last_name or ''}".strip()