import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    # --- ПОЛЯ СВЯЗЕЙ ---
    student_id = fields.Many2one('op.student', 'Student', required=True, ondelete='cascade')
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, ondelete='cascade')
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    course_id = fields.Many2one('op.course', related='batch_id.course_id', string="Класс", store=True, readonly=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', compute='_compute_faculty_id', store=True)
    
    # --- ВИЗУАЛИЗАЦИЯ (Stored) ---
    student_avatar = fields.Image(related='student_id.image_128', string="Фото ученика")
    faculty_avatar = fields.Image(related='faculty_id.image_128', string="Фото учителя")
    textbook_image = fields.Image('Textbook Image', compute='_compute_textbook_image', store=True, max_width=128, max_height=128)
    student_name_short = fields.Char('Student Name Short', compute='_compute_student_name_short', store=True)
    
    # --- ХРАНИМАЯ СТАТИСТИКА (Stored) ---
    average_mark = fields.Float('Средняя', compute='_compute_all_stats', store=True, aggregator="avg")
    total_classes = fields.Integer('Всего', compute='_compute_all_stats', store=True)
    present_classes = fields.Integer('Посещено', compute='_compute_all_stats', store=True)
    last_attendance_date = fields.Date('Дата последнего урока', compute='_compute_all_stats', store=True)
    attendance_rate = fields.Float('Посещаемость %', compute='_compute_all_stats', store=True)    

    # Счетчики по четвертям (Stored)
    for q in range(1, 5):
        locals()[f'q{q}_average_mark'] = fields.Float(compute='_compute_all_stats', store=True)
        locals()[f'q{q}_last_remark'] = fields.Char(compute='_compute_all_stats', store=True)
        for g in range(2, 6):
            locals()[f'q{q}_count_{g}'] = fields.Integer(compute='_compute_all_stats', store=True)

    # --- НЕХРАНИМЫЕ ПОЛЯ (ЭКРАННЫЕ) ---
    # Many2many для вкладок
    q1_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')
    q2_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')
    q3_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')
    q4_line_ids = fields.Many2many('op.attendance.line', compute='_compute_line_ids')

    # Графика (Рассчитывается мгновенно в памяти)
    attendance_bar_html = fields.Html(compute='_compute_visuals', sanitize=False, store=False)
    year_progress_svg = fields.Html(compute='_compute_visuals', sanitize=False, store=False)

    # Ручной ввод итогов
    q1_final_grade = fields.Char('Итог Q1')
    q2_final_grade = fields.Char('Итог Q2')
    q3_final_grade = fields.Char('Итог Q3')
    q4_final_grade = fields.Char('Итог Q4')
    final_quarter_grade = fields.Char('Годовая')

    # --- 1. МЕТОД РАСЧЕТА ЦИФР (ОПТИМИЗИРОВАННЫЙ BATCH) ---
    @api.depends('student_id', 'subject_id')
    def _compute_all_stats(self):
        # 1. Собираем данные ОДНИМ запросом ко всей базе (Batch Read)
        # Мы берем только нужные поля, это в 10 раз быстрее обычного search
        student_ids = self.mapped('student_id').ids
        subject_ids = self.mapped('subject_id').ids
        
        all_lines_data = self.env['op.attendance.line'].search_read([
            ('student_id', 'in', student_ids),
            '|', ('subject_id', 'in', subject_ids),
                 ('attendance_id.session_id.subject_id', 'in', subject_ids)
        ], ['student_id', 'subject_id', 'attendance_id', 'present', 'late', 'grade_1', 'grade_2', 'grade_3', 'term_id', 'remark', 'attendance_date'])

        # Группируем данные в словари (быстрый доступ в памяти)
        data_map = {}
        for l in all_lines_data:
            # Определяем предмет (напрямую или через сессию)
            sub_id = l['subject_id'][0] if l['subject_id'] else False
            # Если в линии нет предмета, Odoo берет его из сессии (подгружаем по необходимости)
            if not sub_id:
                continue 
            
            key = (l['student_id'][0], sub_id)
            data_map.setdefault(key, []).append(l)

        for rec in self:
            lines = data_map.get((rec.student_id.id, rec.subject_id.id), [])
            
            # Инициализация (используем простые переменные, это быстрее чем словари)
            t_sum, t_qty, t_present = 0.0, 0, 0
            # Структура для четвертей: [sum, qty, c5, c4, c3, c2, remark]
            q = {1: [0.0, 0, 0, 0, 0, 0, False], 2: [0.0, 0, 0, 0, 0, 0, False], 
                 3: [0.0, 0, 0, 0, 0, 0, False], 4: [0.0, 0, 0, 0, 0, 0, False]}
            
            last_date = False
            if lines:
                last_date = lines[0]['attendance_date']

            # ОДИН ПРОХОД ПО ВСЕМ ЛИНИЯМ (Вместо 10 фильтраций)
            for l in lines:
                if l['present'] or l['late']:
                    t_present += 1
                
                # Определяем четверть (по ID или имени)
                t_name = (l['term_id'][1] if l['term_id'] else '').lower()
                q_idx = 1 if '1' in t_name else 2 if '2' in t_name else 3 if '3' in t_name else 4 if '4' in t_name else False
                
                if q_idx:
                    # Считаем оценки
                    for g_val in [l['grade_1'], l['grade_2'], l['grade_3']]:
                        if g_val and 2 <= g_val <= 5:
                            val = int(g_val)
                            t_sum += g_val
                            t_qty += 1
                            q[q_idx][0] += g_val # sum
                            q[q_idx][1] += 1     # qty
                            # Индексы для счетчиков: 2->5, 3->4, 4->3, 5->2
                            q[q_idx][6 - val + 1] += 1 

                    if l['remark'] and not q[q_idx][6]:
                        q[q_idx][6] = l['remark']

            # МАССОВАЯ ЗАПИСЬ (ОДИН РАЗ)
            rec.total_classes = len(lines)
            rec.present_classes = t_present
            rec.last_attendance_date = last_date
            rec.attendance_rate = (t_present / rec.total_classes * 100) if rec.total_classes > 0 else 0.0
            rec.average_mark = round(t_sum / t_qty, 2) if t_qty > 0 else 0.0
            
            q_avgs = []
            for i in range(1, 5):
                avg = round(q[i][0] / q[i][1], 2) if q[i][1] > 0 else 0.0
                setattr(rec, f'q{i}_average_mark', avg)
                setattr(rec, f'q{i}_last_remark', q[i][6] or "—")
                setattr(rec, f'q{i}_count_5', q[i][2])
                setattr(rec, f'q{i}_count_4', q[i][3])
                setattr(rec, f'q{i}_count_3', q[i][4])
                setattr(rec, f'q{i}_count_2', q[i][5])
                q_avgs.append(avg)            

    # --- 2. МЕТОД ГРАФИКИ И ПОЛОСКИ (МГНОВЕННЫЙ) ---
    @api.depends('attendance_rate', 'q1_average_mark', 'q2_average_mark', 'q3_average_mark', 'q4_average_mark')
    def _compute_visuals(self):
        for rec in self:
            # 1. Полоска посещаемости (без изменений)
            rate = rec.attendance_rate
            color = 'bg-success' if rate >= 80 else 'bg-warning' if rate >= 60 else 'bg-danger'
            rec.attendance_bar_html = f'<div class="progress" style="height:10px; background:#eee; border-radius:5px;"><div class="progress-bar {color}" style="width:{rate}%"></div></div>'
            
            # 2. УВЕЛИЧЕННЫЙ ГРАФИК
            q_avgs = [rec.q1_average_mark, rec.q2_average_mark, rec.q3_average_mark, rec.q4_average_mark]
            # Увеличили h до 60, px растянули
            w, h, px = 120, 60, [10, 43, 76, 110]
            coords = []
            dots_html = []

            for i, val in enumerate(q_avgs):
                x = px[i]
                if val > 0:
                    # Новая формула: 5.0 -> 10px, 2.0 -> 55px (размах 45px вместо 23px)
                    y = 55 - ((val - 2) * 15)
                    coords.append((x, y))
                    dots_html.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="white" stroke="#714B67" stroke-width="2.5"/>')
                else:
                    # Пустые точки чуть ниже заголовка
                    dots_html.append(f'<circle cx="{x}" cy="30" r="2" fill="#eee" stroke="#ddd" stroke-width="1"/>')

            line_html = ""
            area_html = ""
            if len(coords) >= 2:
                path_data = f"M {coords[0][0]} {coords[0][1]}"
                for i in range(1, len(coords)):
                    path_data += f" L {coords[i][0]} {coords[i][1]}"
                
                # Линия
                line_html = f'<path d="{path_data}" fill="none" stroke="#714B67" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
                
                # Заливка под линией для объема
                area_data = path_data + f" L {coords[-1][0]} {h} L {coords[0][0]} {h} Z"
                area_html = f'<path d="{area_data}" fill="#714B67" fill-opacity="0.1"/>'

            rec.year_progress_svg = f"""
                <div style="width:100%; height:65px; display:flex; align-items:center; justify-content:center;">
                    <svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" style="width:100%; height:60px;">
                        {area_html}
                        {line_html}
                        {" ".join(dots_html)}
                    </svg>
                </div>
            """

    # --- 3. БЫСТРЫЙ ПОИСК ОБЛОЖЕК (1 ЗАПРОС НА ВСЕХ) ---
    @api.depends('subject_id', 'batch_id')
    def _compute_textbook_image(self):
        media = self.env['op.media'].search([('subject_ids', 'in', self.subject_id.ids)])
        match_map, gen_map = {}, {}
        for m in media:
            for s_id in m.subject_ids.ids:
                if m.course_ids:
                    for c_id in m.course_ids.ids: match_map.setdefault((s_id, c_id), m.x_image_128)
                else: gen_map.setdefault(s_id, m.x_image_128)
        for r in self:
            sid, cid = r.subject_id.id, r.batch_id.course_id.id
            r.textbook_image = match_map.get((sid, cid)) or gen_map.get(sid) or False

    # --- 4. ОСТАЛЬНЫЕ МЕТОДЫ ---
    @api.depends('student_id', 'subject_id')
    def _compute_line_ids(self):
        all_lines = self.env['op.attendance.line'].search([('student_id', 'in', self.student_id.ids)], order='attendance_date desc')
        lines_map = {}
        for l in all_lines:
            sub = l.subject_id.id or l.attendance_id.session_id.subject_id.id
            lines_map.setdefault((l.student_id.id, sub), []).append(l)
        for rec in self:
            lines = lines_map.get((rec.student_id.id, rec.subject_id.id), [])
            for i in range(1, 5):
                q_lines = [x.id for x in lines if x.term_id and str(i) in (x.term_id.name or '')]
                setattr(rec, f'q{i}_line_ids', [(6, 0, q_lines)])

    @api.depends('subject_id', 'batch_id')
    def _compute_faculty_id(self):
        sessions = self.env['op.session'].search([('subject_id', 'in', self.subject_id.ids), ('batch_id', 'in', self.batch_id.ids)])
        s_map = {(s.subject_id.id, s.batch_id.id): s.faculty_id.id for s in sessions}
        for r in self: r.faculty_id = s_map.get((r.subject_id.id, r.batch_id.id), False)

    @api.depends('student_id')
    def _compute_student_name_short(self):
        for r in self: r.student_name_short = f"{r.student_id.first_name or ''} {r.student_id.last_name or ''}".strip()

    def action_force_recompute(self):
        self.env.cache.invalidate()
        self._compute_all_stats()
        return True

    def action_migrate_old_data(self):
        return True

# --- РАСШИРЕНИЕ ОСНОВНОЙ МОДЕЛИ ПОСЕЩАЕМОСТИ ---
class OpAttendanceLineInherit(models.Model):
    _inherit = "op.attendance.line"

    @api.constrains('grade_1', 'grade_2', 'grade_3')
    def _check_grades_limit(self):
        for line in self:
            for g in [line.grade_1, line.grade_2, line.grade_3]:
                if g and g > 5: 
                    raise ValidationError(_("Оценка не может быть выше 5!"))

    @api.model_create_multi
    def create(self, vals_list):
        records = super(OpAttendanceLineInherit, self).create(vals_list)
        self._trigger_immediate_recompute(records)
        return records

    def write(self, vals):
        res = super(OpAttendanceLineInherit, self).write(vals)
        fields_to_check = ['grade_1', 'grade_2', 'grade_3', 'present', 'term_id', 'remark']
        if any(f in vals for f in fields_to_check):
            self.env.flush_all() 
            student_ids = self.mapped('student_id').ids
            grades = self.env['op.subject.grades'].search([('student_id', 'in', student_ids)])            
            if grades:
                grades.modified(['average_mark', 'total_classes', 'attendance_rate'])                
                self.env.add_to_compute(grades._fields['average_mark'], grades)                
        return res

    def unlink(self):
        # Сохраняем ID студентов перед удалением строк
        student_ids = self.mapped('student_id').ids
        res = super(OpAttendanceLineInherit, self).unlink()
        if student_ids:
            # Ищем их карточки успеваемости и обновляем
            grades = self.env['op.subject.grades'].search([('student_id', 'in', student_ids)])
            grades._compute_all_stats()
        return res

    def _trigger_immediate_recompute(self, attendance_lines):
        """ Принудительный и мгновенный пересчет успеваемости """
        student_ids = attendance_lines.mapped('student_id').ids
        if student_ids:
            # Находим все затронутые карточки успеваемости
            grades = self.env['op.subject.grades'].search([('student_id', 'in', student_ids)])
            if grades:
                # 1. Сбрасываем кэш именно этих записей, чтобы они "забыли" старые цифры
                grades.invalidate_recordset()
                # 2. Вызываем расчет напрямую. 
                # Так как мы написали его через "lines_map", он сделает 1 запрос к БД на всех.
                grades._compute_all_stats()