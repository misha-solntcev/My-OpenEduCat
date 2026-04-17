import re
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    # --- БАЗОВЫЕ ПОЛЯ ---
    student_id = fields.Many2one('op.student', 'Student', required=True, ondelete='cascade')
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, ondelete='cascade')
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    course_id = fields.Many2one('op.course', related='batch_id.course_id', string="Класс", store=True, readonly=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', compute='_compute_faculty_id', store=True)
    
    table_entries = fields.Text('Table Entries') # Для миграции
    
    # --- ВИЗУАЛИЗАЦИЯ (Не храним фото в этой модели, тянем из оригиналов) ---
    student_avatar = fields.Image(related='student_id.image_128', string="Фото ученика", store=False)
    faculty_avatar = fields.Image(related='faculty_id.image_128', string="Фото учителя", store=False)
    textbook_image = fields.Image('Textbook Image', compute='_compute_textbook_image', store=True, max_width=128, max_height=128)
    student_name_short = fields.Char('Student Name Short', compute='_compute_student_name_short', store=True)
    
    # --- ХРАНИМАЯ СТАТИСТИКА (STORED) ---
    average_mark = fields.Float('Средняя', compute='_compute_all_stats', store=True, aggregator="avg")
    total_classes = fields.Integer('Всего', compute='_compute_all_stats', store=True)
    present_classes = fields.Integer('Посещено', compute='_compute_all_stats', store=True)
    last_attendance_date = fields.Date('Дата последнего урока', compute='_compute_all_stats', store=True)
    attendance_rate = fields.Float('Посещаемость %', compute='_compute_all_stats', store=True)

    for q in range(1, 5):
        locals()[f'q{q}_average_mark'] = fields.Float(compute='_compute_all_stats', store=True)
        locals()[f'q{q}_last_remark'] = fields.Char(compute='_compute_all_stats', store=True)
        for g in range(2, 6):
            locals()[f'q{q}_count_{g}'] = fields.Integer(compute='_compute_all_stats', store=True)

    # --- ЭКРАННЫЕ ПОЛЯ (NON-STORED) ---
    q1_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')
    q2_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')
    q3_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')
    q4_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')

    attendance_bar_html = fields.Html(compute='_compute_visuals', sanitize=False, store=False)
    year_progress_svg = fields.Html(compute='_compute_visuals', sanitize=False, store=False)

    for q in range(1, 5):
        locals()[f'q{q}_attendance_stats_html'] = fields.Html(compute='_compute_attendance_stats_html', sanitize=False, store=False)

    # Ручной ввод итогов
    q1_final_grade = fields.Char('Итог Q1')
    q2_final_grade = fields.Char('Итог Q2')
    q3_final_grade = fields.Char('Итог Q3')
    q4_final_grade = fields.Char('Итог Q4')
    final_quarter_grade = fields.Char('Годовая')

    # --- МЕТОДЫ РАСЧЕТА ---

    @api.depends('student_id', 'subject_id')
    def _compute_all_stats(self):
        # --- ОПТИМИЗАЦИЯ №1: ОДИН ЗАПРОС НА ВЕСЬ НАБОР ---
        student_ids = self.student_id.ids
        subject_ids = self.subject_id.ids
        
        all_lines = self.env['op.attendance.line'].search([
            ('student_id', 'in', student_ids),
            ('subject_id', 'in', subject_ids)
        ])
        
        # Группируем линии в словарь для мгновенного доступа в цикле
        # Ключ: (student_id, subject_id)
        lines_dict = {}
        for l in all_lines:
            key = (l.student_id.id, l.subject_id.id)
            if key not in lines_dict:
                lines_dict[key] = self.env['op.attendance.line']
            lines_dict[key] |= l

        for rec in self:
            # Вместо поиска в базе берем готовый набор из словаря
            my_lines = lines_dict.get((rec.student_id.id, rec.subject_id.id), self.env['op.attendance.line'])
            
            # Используем наш "движок" из attendance_line
            full = self.env['op.attendance.line'].get_stats_from_lines(my_lines)
            
            rec.total_classes = full['total']
            rec.present_classes = full['present']
            rec.attendance_rate = full['rate']
            rec.average_mark = full['avg']
            rec.last_attendance_date = full['last_date']

            for i in range(1, 5):
                # Фильтруем маленький RecordSet в памяти (это очень быстро)
                q_lines = my_lines.filtered(lambda x: x.term_id and str(i) in (x.term_id.name or ''))
                q = self.env['op.attendance.line'].get_stats_from_lines(q_lines)
                
                setattr(rec, f'q{i}_average_mark', q['avg'])
                setattr(rec, f'q{i}_last_remark', q['last_remark'])
                # stats_html и counts тоже заполняем здесь, если они в этом методе
                setattr(rec, f'q{i}_count_5', q['counts'][5])
                setattr(rec, f'q{i}_count_4', q['counts'][4])
                setattr(rec, f'q{i}_count_3', q['counts'][3])
                setattr(rec, f'q{i}_count_2', q['counts'][2])

    @api.depends('student_id', 'subject_id', 'q1_line_ids', 'q2_line_ids', 'q3_line_ids', 'q4_line_ids')
    def _compute_attendance_stats_html(self):
        line_obj = self.env['op.attendance.line']
        for rec in self:
            for i in range(1, 5):
                # Просто просим движок дать статистику для строк текущей четверти
                lines = getattr(rec, f'q{i}_line_ids')
                q_stats = line_obj.get_stats_from_lines(lines)
                
                # Забираем уже ГОТОВЫЙ HTML из движка
                setattr(rec, f'q{i}_attendance_stats_html', q_stats['html_summary'] or "Нет данных")

    @api.depends('attendance_rate', 'q1_average_mark', 'q2_average_mark', 'q3_average_mark', 'q4_average_mark')
    def _compute_visuals(self):
        for rec in self:
            # 1. Полоска посещаемости (без изменений)
            rate = rec.attendance_rate
            color = 'bg-success' if rate >= 80 else 'bg-warning' if rate >= 60 else 'bg-danger'
            rec.attendance_bar_html = f'<div class="progress" style="height:10px; background:#eee; border-radius:5px;"><div class="progress-bar {color}" style="width:{rate}%"></div></div>'
            
            # 2. ГРАФИК "FULL SIZE"
            q_avgs = [rec.q1_average_mark, rec.q2_average_mark, rec.q3_average_mark, rec.q4_average_mark]
            # Увеличиваем вертикальный масштаб: 400x160
            w, h = 400, 160
            # Раздвигаем точки X максимально: 30, 143, 256, 370
            px = [30, 143, 256, 370]
            
            coords = []
            dots_html = []
            for i, val in enumerate(q_avgs):
                x = px[i]
                if val > 0:
                    # Размах по Y теперь 110 единиц (от 30 до 140)
                    y = 140 - ((val - 2) * 36.6)
                    coords.append((x, y))
                    # Крупные белые точки с жирным контуром
                    dots_html.append(f'<circle cx="{x}" cy="{y}" r="7" fill="white" stroke="#714B67" stroke-width="5"/>')
                else:
                    # Плейсхолдеры (серые точки) на базовой линии
                    dots_html.append(f'<circle cx="{x}" cy="80" r="5" fill="#f0f0f0" stroke="#ccc" stroke-width="2"/>')

            graph_content = ""
            if len(coords) >= 2:
                path_data = f"M {coords[0][0]} {coords[0][1]}"
                for i in range(1, len(coords)):
                    path_data += f" L {coords[i][0]} {coords[i][1]}"
                
                area_data = path_data + f" L {coords[-1][0]} {h} L {coords[0][0]} {h} Z"
                grad_id = f"grad_final_{rec.id or 'new'}"
                
                graph_content = f"""
                    <defs>
                        <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#714B67; stop-opacity:0.25" />
                            <stop offset="100%" style="stop-color:#714B67; stop-opacity:0" />
                        </linearGradient>
                    </defs>
                    <path d="{area_data}" fill="url(#{grad_id})" />
                    <path d="{path_data}" fill="none" stroke="#714B67" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
                """

            # Убираем все ограничения по высоте в стиле, даем 100%
            rec.year_progress_svg = f"""
                <svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" style="width:100%; height:100px; display:block; margin:0;">
                    <!-- Сетка: уровни 5.0, 3.5, 2.0 -->
                    <text x="1" y="35" font-family="sans-serif" font-size="20" fill="#adb5bd" font-weight="bold">5</text>
                    <line x1="35" y1="30" x2="{w}" y2="30" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
                    <text x="1" y="71" font-family="sans-serif" font-size="20" fill="#adb5bd" font-weight="bold">4</text>
                    <line x1="25" y1="66" x2="{w}" y2="66" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
                    <text x="1" y="108" font-family="sans-serif" font-size="20" fill="#adb5bd" font-weight="bold">3</text>
                    <line x1="25" y1="103" x2="{w}" y2="103" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
                    <text x="1" y="145" font-family="sans-serif" font-size="20" fill="#adb5bd" font-weight="bold">2</text>
                    <line x1="25" y1="140" x2="{w}" y2="140" stroke="#e0e0e0" stroke-width="2" stroke-dasharray="4,4"/>
                    {graph_content}
                    {" ".join(dots_html)}
                </svg>
            """

    @api.depends('subject_id', 'batch_id')
    def _compute_faculty_id(self):
        sessions = self.env['op.session'].search([('subject_id', 'in', self.subject_id.ids), ('batch_id', 'in', self.batch_id.ids)])
        s_map = {(s.subject_id.id, s.batch_id.id): s.faculty_id.id for s in sessions}
        for r in self: r.faculty_id = s_map.get((r.subject_id.id, r.batch_id.id), False)

    @api.depends('subject_id', 'batch_id')
    def _compute_textbook_image(self):
        media = self.env['op.media'].search([('subject_ids', 'in', self.subject_id.ids)])
        m_map, g_map = {}, {}
        for m in media:
            for s_id in m.subject_ids.ids:
                if m.course_ids: 
                    for c_id in m.course_ids.ids: m_map[(s_id, c_id)] = m.x_image_128
                else: g_map[s_id] = m.x_image_128
        for r in self:
            sid, cid = r.subject_id.id, r.batch_id.course_id.id
            r.textbook_image = m_map.get((sid, cid)) or g_map.get(sid) or False

    @api.depends('student_id')
    def _compute_student_name_short(self):
        for r in self: r.student_name_short = f"{r.student_id.first_name or ''} {r.student_id.last_name or ''}".strip()

    @api.depends('student_id', 'subject_id')
    def _compute_line_ids(self):
        # Аналогично оптимизируем Many2many списки
        all_lines = self.env['op.attendance.line'].search([('student_id', 'in', self.student_id.ids)])
        
        lines_dict = {}
        for l in all_lines:
            sub = l.subject_id.id or l.attendance_id.session_id.subject_id.id
            key = (l.student_id.id, sub)
            if key not in lines_dict: lines_dict[key] = []
            lines_dict[key].append(l.id)

        for rec in self:
            my_ids = lines_dict.get((rec.student_id.id, rec.subject_id.id), [])
            # Odoo подтянет объекты по ID сам
            lines_objs = self.env['op.attendance.line'].browse(my_ids)
            for i in range(1, 5):
                q_ids = lines_objs.filtered(lambda x: x.term_id and str(i) in (x.term_id.name or '')).ids
                setattr(rec, f'q{i}_line_ids', [(6, 0, q_ids)])
    def action_force_recompute(self):
        self.env.cache.invalidate()
        self._compute_all_stats()
        return True

    # --- ВОССТАНОВЛЕННАЯ МИГРАЦИЯ ---
    def action_migrate_old_data(self):
        records = self if self else self.search([])
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        total_m = 0
        for record in records.sudo():
            if not record.table_entries: continue
            student_lines = self.env['op.attendance.line'].search([('student_id', '=', record.student_id.id)])
            cache = {(str(l.attendance_date), (l.subject_id.id or l.attendance_id.session_id.subject_id.id)): l for l in student_lines}
            raw = record.table_entries.split(',')
            valid = []
            for p in raw:
                p = p.strip()
                if p.startswith('202'): valid.append(p)
                elif valid: valid[-1] += "," + p
            for entry in valid:
                parts = [p.strip() for p in entry.split('|')]
                if len(parts) < 2 or not date_pattern.match(parts[0]): continue
                line = cache.get((parts[0], record.subject_id.id))
                if line:
                    try:
                        vals = {}
                        if parts[1] not in ['', 'None', 'False']: vals['grade_1'] = float(parts[1].replace(',', '.'))
                        if len(parts) > 2 and parts[2] not in ['', 'None', 'False']: vals['grade_2'] = float(parts[2].replace(',', '.'))
                        if len(parts) > 7 and parts[7]: vals['remark'] = parts[7]
                        if vals: line.write(vals); total_m += 1
                    except: pass
        return True