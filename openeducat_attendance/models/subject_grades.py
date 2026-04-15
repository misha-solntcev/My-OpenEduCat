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
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, ondelete='cascade')
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', compute='_compute_faculty_id', store=True)
    
    table_entries = fields.Text('Table Entries') 
    textbook_image = fields.Binary('Textbook Image', compute='_compute_textbook_image', store=True)
    student_name_short = fields.Char('Student Name Short', compute='_compute_student_name_short', store=True)
    
    # --- Итоги (Stored) ---
    average_mark = fields.Float('Средняя', compute='_compute_all_stats', store=True, aggregator="avg")
    total_classes = fields.Integer('Всего', compute='_compute_all_stats', store=True)
    present_classes = fields.Integer('Посещено', compute='_compute_all_stats', store=True)
    last_attendance_date = fields.Date('Дата последнего урока', compute='_compute_all_stats', store=True)

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

    @api.depends('student_id', 'subject_id')
    def _compute_all_stats(self):
        for rec in self:
            res = {'ts': 0.0, 'tq': 0, 'q': {i: {'s': 0.0, 'q': 0, 'c5': 0, 'c4': 0, 'c3': 0, 'c2': 0, 'r': False} for i in range(1, 5)}}
            
            lines = self.env['op.attendance.line'].search([
                ('student_id', '=', rec.student_id.id),
                '|', ('subject_id', '=', rec.subject_id.id),
                     ('attendance_id.session_id.subject_id', '=', rec.subject_id.id)
            ], order='attendance_date desc')

            rec.total_classes = len(lines)
            rec.present_classes = len(lines.filtered(lambda x: x.present or x.late))
            rec.last_attendance_date = lines[0].attendance_date if lines else False

            for l in lines:
                t_name = (l.term_id.name or '').lower()
                q_idx = next((i for i in range(1, 5) if str(i) in t_name), None)
                if not q_idx: continue

                # Расчет среднего балла (валидация теперь на уровне модели lines)
                for g in [l.grade_1, l.grade_2, l.grade_3]:
                    if g and g > 0:
                        val = int(g)
                        res['ts'] += g; res['tq'] += 1
                        res['q'][q_idx]['s'] += g; res['q'][q_idx]['q'] += 1
                        if 2 <= val <= 5: 
                            res['q'][q_idx][f'c{val}'] += 1
                
                if l.remark and not res['q'][q_idx]['r']:
                    res['q'][q_idx]['r'] = l.remark

            rec.average_mark = round(res['ts'] / res['tq'], 2) if res['tq'] > 0 else 0.0
            for i in range(1, 5):
                setattr(rec, f'q{i}_average_mark', round(res['q'][i]['s'] / res['q'][i]['q'], 2) if res['q'][i]['q'] > 0 else 0.0)
                setattr(rec, f'q{i}_last_remark', res['q'][i]['r'])
                for g in range(2, 6): setattr(rec, f'q{i}_count_{g}', res['q'][i][f'c{g}'])

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

    # Триггеры пересчета успеваемости
    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['grade_1', 'grade_2', 'grade_3', 'present', 'term_id', 'remark']):
            self.flush_recordset() 
            grade_recs = self.env['op.subject.grades'].search([('student_id', '=', self.student_id.id)])
            for g in grade_recs: g._compute_all_stats()
        return res

    def create(self, vals):
        res = super().create(vals)
        self.env['op.subject.grades'].search([('student_id', '=', res.student_id.id)])._compute_all_stats()
        return res