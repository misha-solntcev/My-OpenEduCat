from odoo import api, fields, models, _, fields
from odoo.exceptions import ValidationError

class OpAttendanceLine(models.Model):
    _name = "op.attendance.line"
    _inherit = ["mail.thread"]
    _description = "Attendance Lines"
    _order = "attendance_date desc, student_id"

    # --- БАЗОВЫЕ ПОЛЯ ---
    attendance_id = fields.Many2one('op.attendance.sheet', 'Attendance Sheet', 
        required=True, ondelete="cascade", index=True)
    student_id = fields.Many2one('op.student', 'Student', required=True, index=True)
    
    # --- RELATED ПОЛЯ (Для поиска, группировки и Pivot) ---
    attendance_date = fields.Date(related='attendance_id.attendance_date', 
        store=True, readonly=True, index=True, string='Дата занятия')
    subject_id = fields.Many2one('op.subject', related='attendance_id.subject_id', 
        store=True, readonly=True, index=True, string='Предмет')
    batch_id = fields.Many2one('op.batch', related='attendance_id.batch_id', 
        store=True, readonly=True, index=True, string='Класс')    
    faculty_id = fields.Many2one('op.faculty', related='attendance_id.faculty_id', 
        store=True, readonly=True, index=True, string='Учитель')
    
    # Периоды для Pivot-таблицы
    term_id = fields.Many2one('op.academic.term', related='attendance_id.term_id', store=True, readonly=True, index=True, string='Четверть')
    academic_year_id = fields.Many2one('op.academic.year', related='term_id.academic_year_id', 
        store=True, readonly=True, index=True, string='Учебный год')
    parent_term_id = fields.Many2one('op.academic.term', related='term_id.parent_term', 
        store=True, readonly=True, index=True, string='Полугодие')

    lesson_topic = fields.Char(related='attendance_id.lesson_topic', store=True, readonly=True)

    # --- СТАТУСЫ ---
    attendance_type_id = fields.Many2one('op.attendance.type', string='Status', tracking=True)
    present = fields.Boolean(related='attendance_type_id.present', store=True)
    absent = fields.Boolean(related='attendance_type_id.absent', store=True)
    late = fields.Boolean(related='attendance_type_id.late', store=True)
    excused = fields.Boolean(related='attendance_type_id.excused', store=True)

    # --- ОЦЕНКИ ---
    grade_1 = fields.Float('Оценка 1', default=0.0, tracking=True, aggregator="avg")
    grade_2 = fields.Float('Оценка 2', default=0.0, tracking=True, aggregator="avg")
    grade_3 = fields.Float('Оценка 3', default=0.0, tracking=True, aggregator="avg")
    
    grade_1_ui = fields.Selection([('2','2'),('3','3'),('4','4'),('5','5')], string='О1', 
        compute='_compute_grade_ui', inverse='_set_grade_1_ui')
    grade_2_ui = fields.Selection([('2','2'),('3','3'),('4','4'),('5','5')], string='О2', 
        compute='_compute_grade_ui', inverse='_set_grade_2_ui')
    grade_3_ui = fields.Selection([('2','2'),('3','3'),('4','4'),('5','5')], string='О3', 
        compute='_compute_grade_ui', inverse='_set_grade_3_ui')

    grade_avg = fields.Float('Средний балл', compute='_compute_grade_avg', store=True, aggregator="avg")
    remark = fields.Char('Remark', size=256)
    color = fields.Integer(related='attendance_type_id.color')
    student_avatar = fields.Image(related='student_id.image_128', string="Фото")

    # --- ЛОГИКА ОЦЕНОК ---
    @api.depends('grade_1', 'grade_2', 'grade_3')
    def _compute_grade_ui(self):
        for rec in self:
            rec.grade_1_ui = str(int(rec.grade_1)) if rec.grade_1 > 0 else False
            rec.grade_2_ui = str(int(rec.grade_2)) if rec.grade_2 > 0 else False
            rec.grade_3_ui = str(int(rec.grade_3)) if rec.grade_3 > 0 else False

    def _set_grade_1_ui(self):
        for rec in self: rec.grade_1 = float(rec.grade_1_ui) if rec.grade_1_ui else 0.0
    def _set_grade_2_ui(self):
        for rec in self: rec.grade_2 = float(rec.grade_2_ui) if rec.grade_2_ui else 0.0
    def _set_grade_3_ui(self):
        for rec in self: rec.grade_3 = float(rec.grade_3_ui) if rec.grade_3_ui else 0.0

    @api.depends('grade_1', 'grade_2', 'grade_3')
    def _compute_grade_avg(self):
        for rec in self:
            marks = [m for m in [rec.grade_1, rec.grade_2, rec.grade_3] if m > 0]
            rec.grade_avg = sum(marks) / len(marks) if marks else 0.0

    # --- АВТОМАТИЗАЦИЯ ---
    @api.onchange('grade_1_ui', 'grade_2_ui', 'grade_3_ui')
    def _onchange_grades_auto_present(self):
        """
        Логика: если поставили оценку, а статус ПУСТОЙ — ставим 'Присутствует'.
        Если статус УЖЕ стоит (например, 'Болеет'), мы его НЕ ТРОГАЕМ.
        """
        if any([self.grade_1_ui, self.grade_2_ui, self.grade_3_ui]):
            if not self.attendance_type_id:
                p_type = self.env['op.attendance.type'].search([('present', '=', True)], limit=1)
                if p_type:
                    self.attendance_type_id = p_type

    @api.onchange('attendance_type_id')
    def _onchange_attendance_type(self):
        pass

    # --- ПРОВЕРКИ ---
    @api.constrains('grade_1', 'grade_2', 'grade_3')
    def _check_grades_range(self):
        for rec in self:
            for g in [rec.grade_1, rec.grade_2, rec.grade_3]:
                if g > 0 and (g < 2 or g > 5):
                    raise ValidationError(_("Оценка должна быть от 2 до 5!"))

    @api.model
    def get_stats_from_lines(self, lines):
        """Метод-движок: рассчитывает всю математику для графиков и статистики"""
        res = {
            'avg': 0.0, 
            'total': len(lines),
            'present': 0, 'absent': 0, 'late': 0, 'excused': 0,
            'counts': {5: 0, 4: 0, 3: 0, 2: 0},
            'last_remark': "—", 
            'rate': 0.0,
            'types_detailed': {}, 
        }
        if not lines: 
            return res

        marks = []
        type_counts = {}

        # Сортируем линии от новых к старым (чтобы взять актуальный отзыв)
        sorted_l = lines.sorted('attendance_date', reverse=True)

        for l in sorted_l:
            # 1. Посещаемость
            if l.present: res['present'] += 1
            if l.absent: res['absent'] += 1
            if l.late: res['late'] += 1
            if l.excused: res['excused'] += 1

            # 2. Детализация для "бублика"
            if l.attendance_type_id:
                name = l.attendance_type_id.name
                type_counts[name] = type_counts.get(name, 0) + 1

            # 3. Сбор оценок (из всех трех колонок)
            for v in [l.grade_1, l.grade_2, l.grade_3]:
                if v and 2 <= v <= 5:
                    marks.append(v)
                    res['counts'][int(v)] += 1
            
            # 4. Берем самое последнее примечание
            if l.remark and res['last_remark'] == "—":
                res['last_remark'] = l.remark

        # Финальные расчеты
        if marks:
            res['avg'] = round(sum(marks) / len(marks), 2)
        
        if res['total'] > 0:
            # Считаем процент посещаемости (явка / общее кол-во уроков)
            res['rate'] = round(res['present'] / res['total'] * 100, 2)
        
        res['types_detailed'] = type_counts 

        return res

    # --- ДЕЙСТВИЯ ---
    def action_open_sheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Журнал урока'),
            'res_model': 'op.attendance.sheet',
            'view_mode': 'form',
            'res_id': self.attendance_id.id,
            'target': 'current',
        }

    def action_clear_line_data(self):
        self.write({
            'attendance_type_id': False,
            'grade_1': 0.0,
            'grade_2': 0.0,
            'grade_3': 0.0,
            'remark': False,
        })