import re
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    student_id = fields.Many2one('op.student', 'Student', required=True, ondelete='cascade')
    student_avatar = fields.Image(related='student_id.image_128', string="Фото ученика")
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, ondelete='cascade')
    course_id = fields.Many2one('op.course', related='batch_id.course_id', string="Класс", store=True, readonly=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', compute='_compute_faculty_id', store=True)
    faculty_avatar = fields.Image(related='faculty_id.image_128', string="Фото учителя", readonly=True)
    
    table_entries = fields.Text('Table Entries') 
    textbook_image = fields.Image('Textbook Image', compute='_compute_textbook_image', store=True, max_width=128, max_height=128)
    student_name_short = fields.Char('Student Name Short', compute='_compute_student_name_short', store=True)
    
    # --- Итоги (Stored) ---
    average_mark = fields.Float('Средняя', compute='_compute_all_stats', store=True, aggregator="avg")
    total_classes = fields.Integer('Всего', compute='_compute_all_stats', store=True)
    present_classes = fields.Integer('Посещено', compute='_compute_all_stats', store=True)
    last_attendance_date = fields.Date('Дата последнего урока', compute='_compute_all_stats', store=True)
    attendance_rate = fields.Float('Посещаемость %', compute='_compute_all_stats', store=True)

    attendance_bar_html = fields.Html(compute='_compute_attendance_bar', string="Виджет посещаемости")

    # --- Списки линий (Editable) ---
    q1_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids', readonly=False)
    q2_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids', readonly=False)
    q3_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids', readonly=False)
    q4_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids', readonly=False)

    # --- Статистика (Stored) ---
    for q in range(1, 5):
        locals()[f'q{q}_average_mark'] = fields.Float(compute='_compute_all_stats', store=True)
        locals()[f'q{q}_last_remark'] = fields.Char(compute='_compute_all_stats', store=True)
        for g in range(2, 6):
            locals()[f'q{q}_count_{g}'] = fields.Integer(compute='_compute_all_stats', store=True)

    q1_final_grade = fields.Char('Итог Q1')
    q2_final_grade = fields.Char('Итог Q2')
    q3_final_grade = fields.Char('Итог Q3')
    q4_final_grade = fields.Char('Итог Q4')
    final_quarter_grade = fields.Char('Годовая')

    # Математическое среднее по четвертям (не по всем оценкам сразу, а именно по итогам периодов)
    year_average_mark = fields.Float('Средняя за год', compute='_compute_all_stats', store=True)
    # Поле для хранения SVG-кода графика
    year_progress_svg = fields.Html(compute='_compute_all_stats', string="График прогресса", sanitize=False, store=True)

    @api.depends('student_id', 'subject_id')
    def _compute_all_stats(self):
        for rec in self:
            # 1. Инициализация и обнуление
            res = {'ts': 0.0, 'tq': 0, 'q': {i: {'s': 0.0, 'q': 0, 'c5': 0, 'c4': 0, 'c3': 0, 'c2': 0, 'r': False} for i in range(1, 5)}}
            
            lines = self.env['op.attendance.line'].search([
                ('student_id', '=', rec.student_id.id),
                '|', ('subject_id', '=', rec.subject_id.id),
                     ('attendance_id.session_id.subject_id', '=', rec.subject_id.id)
            ], order='attendance_date desc')

            rec.total_classes = len(lines)
            rec.present_classes = len(lines.filtered(lambda x: x.present or x.late))
            rec.last_attendance_date = lines[0].attendance_date if lines else False
            rec.attendance_rate = (rec.present_classes / rec.total_classes * 100) if rec.total_classes > 0 else 0.0

            # 2. Расчет четвертей
            q_avgs = []
            for l in lines:
                t_name = (l.term_id.name or '').lower()
                q_idx = next((i for i in range(1, 5) if str(i) in t_name), None)
                if not q_idx: continue
                for g in [l.grade_1, l.grade_2, l.grade_3]:
                    if g and 2 <= g <= 5:
                        res['ts'] += g; res['tq'] += 1
                        res['q'][q_idx]['s'] += g; res['q'][q_idx]['q'] += 1
                        res['q'][q_idx][f'c{int(g)}'] += 1
                if l.remark and not res['q'][q_idx]['r']:
                    res['q'][q_idx]['r'] = l.remark

            rec.average_mark = round(res['ts'] / res['tq'], 2) if res['tq'] > 0 else 0.0
            
            for i in range(1, 5):
                q_val = round(res['q'][i]['s'] / res['q'][i]['q'], 2) if res['q'][i]['q'] > 0 else 0.0
                setattr(rec, f'q{i}_average_mark', q_val)
                setattr(rec, f'q{i}_last_remark', res['q'][i]['r'] or "—")
                for g in range(2, 6): setattr(rec, f'q{i}_count_{g}', res['q'][i][f'c{g}'])
                q_avgs.append(q_val)

            # Годовая
            active_qs = [v for v in q_avgs if v > 0]
            rec.year_average_mark = round(sum(active_qs) / len(active_qs), 2) if active_qs else 0.0

            # 3. ГЕНЕРАЦИЯ ГРАФИКА (ТЕПЕРЬ ТУТ)
            w, h, px = 120, 40, [15, 45, 75, 105]
            coords = []
            for i, val in enumerate(q_avgs):
                if val > 0:
                    y = 35 - ((val - 2) * 10) # 5.0 -> 5px, 2.0 -> 35px
                    coords.append((px[i], y))

            if not coords:
                rec.year_progress_svg = '<div class="text-muted small">Нет оценок</div>'
                continue

            # Рисуем Area Chart (линия + заливка)
            color = "#714B67"
            path = f"M {coords[0][0]} {coords[0][1]}"
            for i in range(1, len(coords)): path += f" L {coords[i][0]} {coords[i][1]}"
            area = path + f" L {coords[-1][0]} {h} L {coords[0][0]} {h} Z"

            rec.year_progress_svg = f"""
                <div style="width:100%; height:45px; display:flex; align-items:center; justify-content:center;">
                    <svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">
                        <defs><linearGradient id="g_{rec.id}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:{color}; stop-opacity:0.2" />
                            <stop offset="100%" style="stop-color:{color}; stop-opacity:0" />
                        </linearGradient></defs>
                        <line x1="10" y1="5" x2="110" y2="5" stroke="#eee" stroke-width="0.5"/>
                        <line x1="10" y1="35" x2="110" y2="35" stroke="#eee" stroke-width="0.5"/>
                        {f'<path d="{area}" fill="url(#g_{rec.id})" />' if len(coords)>1 else ''}
                        {f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>' if len(coords)>1 else ''}
                        {" ".join([f'<circle cx="{c[0]}" cy="{c[1]}" r="2.5" fill="white" stroke="{color}" stroke-width="2"/>' for c in coords])}
                    </svg>
                </div>
            """

    @api.depends('attendance_rate')
    def _compute_attendance_bar(self):
        for rec in self:
            rate = rec.attendance_rate
            # Логика цвета
            color = 'bg-danger'
            if rate >= 80: color = 'bg-success'
            elif rate >= 60: color = 'bg-warning'
            
            # Генерируем только HTML, не трогая основную статистику
            rec.attendance_bar_html = f"""
                <div class="progress" style="height: 10px; background-color: #eee; border-radius: 5px;">
                    <div class="progress-bar {color}" role="progressbar" style="width: {rate}%;"></div>
                </div>
            """

    @api.depends('student_id', 'subject_id')
    def _compute_line_ids(self):
        for rec in self:
            lines = self.env['op.attendance.line'].search([
                ('student_id', '=', rec.student_id.id),
                '|', ('subject_id', '=', rec.subject_id.id),
                     ('attendance_id.session_id.subject_id', '=', rec.subject_id.id)
            ], order='attendance_date desc')
            for i in range(1, 5):
                q_lines = lines.filtered(lambda x: x.term_id and str(i) in (x.term_id.name or ''))
                setattr(rec, f'q{i}_line_ids', [(6, 0, q_lines.ids)])

    def action_force_recompute(self):
        """ Принудительное обновление ВСЕГО (для фикса пустых полей) """
        self.env.invalidate_all()
        # Запускаем расчеты для всего набора записей
        self._compute_faculty_id()
        self._compute_student_name_short()
        self._compute_textbook_image()
        self._compute_all_stats()
        _logger.info("=== ПЕРЕСЧЕТ ЗАВЕРШЕН: КАРТИНКИ И СТАТИСТИКА ОБНОВЛЕНЫ ===")
        return True

    @api.depends('subject_id', 'batch_id')
    def _compute_faculty_id(self):
        s_ids = self.mapped('subject_id').ids
        b_ids = self.mapped('batch_id').ids
        sessions = self.env['op.session'].search([('subject_id', 'in', s_ids), ('batch_id', 'in', b_ids)])
        s_map = {(s.subject_id.id, s.batch_id.id): s.faculty_id.id for s in sessions}
        for r in self: r.faculty_id = s_map.get((r.subject_id.id, r.batch_id.id), False)

    @api.depends('student_id')
    def _compute_student_name_short(self):
        for r in self: r.student_name_short = f"{r.student_id.first_name or ''} {r.student_id.last_name or ''}".strip()

    @api.depends('subject_id', 'batch_id')
    def _compute_textbook_image(self):
        s_ids = self.mapped('subject_id').ids
        media = self.env['op.media'].search([('subject_ids', 'in', s_ids)])
        m_map, g_map = {}, {}
        for m in media:
            img = m.x_image_128
            if not img: continue
            for sid in m.subject_ids.ids:
                if m.course_ids: 
                    for cid in m.course_ids.ids: m_map[(sid, cid)] = img
                else: g_map[sid] = img
        for r in self:
            sid, cid = r.subject_id.id, r.batch_id.course_id.id
            r.textbook_image = m_map.get((sid, cid)) or g_map.get(sid) or False

    def action_migrate_old_data(self):
        return True

# --- РАСШИРЕНИЕ ОСНОВНОЙ МОДЕЛИ ПОСЕЩАЕМОСТИ ---
class OpAttendanceLineInherit(models.Model):
    _inherit = "op.attendance.line"

    # Валидация на уровне БД и интерфейса
    @api.constrains('grade_1', 'grade_2', 'grade_3')
    def _check_grades_limit(self):
        for line in self:
            for g in [line.grade_1, line.grade_2, line.grade_3]:
                if g and g > 5:
                    raise ValidationError(_("Ошибка: Оценка %s недопустима. Оценка не может быть выше 5!") % g)

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['grade_1', 'grade_2', 'grade_3', 'present', 'term_id', 'remark']):
            # Находим и ПРИНУДИТЕЛЬНО пересчитываем успеваемость
            grades = self.env['op.subject.grades'].search([('student_id', '=', self.student_id.id)])
            for g in grades:
                g.invalidate_recordset() # Сброс кеша
                g._compute_all_stats()   # Расчет цифр и графика
        return res

    def create(self, vals):
        res = super().create(vals)
        self.env['op.subject.grades'].search([('student_id', '=', res.student_id.id)])._compute_all_stats()
        return res