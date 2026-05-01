###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import api, fields, models
from odoo.tools import SQL


class OpAttendanceLine(models.Model):
    _name = "op.attendance.line"
    _inherit = ["mail.thread"]
    _rec_name = "attendance_id"
    _description = "Attendance Lines"
    _order = "attendance_date desc"

    attendance_id = fields.Many2one(
        'op.attendance.sheet', 'Attendance Sheet', required=True,
        tracking=True, ondelete="cascade")
    student_id = fields.Many2one(
        'op.student', 'Student', required=True, tracking=True)
    register_id = fields.Many2one(
        related='attendance_id.register_id', store=True, readonly=True)
    
    attendance_date = fields.Date(
        'Date', related='attendance_id.attendance_date', store=True,
        readonly=True, tracking=True)
    
    subject_id = fields.Many2one(
        'op.subject', string='Предмет', 
        related='attendance_id.subject_id', store=True, readonly=True)

    term_id = fields.Many2one(
        'op.academic.term', string='Четверть', 
        related='attendance_id.term_id', store=True, readonly=True)
    
    academic_year_id = fields.Many2one(
        'op.academic.year', string='Учебный год', 
        related='term_id.academic_year_id', store=True, readonly=True)

    parent_term_id = fields.Many2one(
        'op.academic.term', string='Полугодие', 
        related='term_id.parent_term', store=True, readonly=True)

    course_id = fields.Many2one(
        'op.course', 'Course',
        related='attendance_id.register_id.course_id', store=True, readonly=True)
    
    batch_id = fields.Many2one(
        'op.batch', 'Batch',
        related='attendance_id.register_id.batch_id', store=True, readonly=True)

    faculty_id = fields.Many2one(
        'op.faculty', 'Faculty', 
        related='attendance_id.faculty_id', store=True, readonly=True)

    lesson_topic = fields.Char(
        'Lesson Topic', related='attendance_id.lesson_topic', store=True, readonly=False)

    remark = fields.Char('Remark', size=256, tracking=True)
    active = fields.Boolean(default=True)

    student_avatar = fields.Image(related='student_id.image_128', string="Фото", readonly=True)

    attendance_type_id = fields.Many2one(
        'op.attendance.type', string='Status', required=False, tracking=True)
    color = fields.Integer(related='attendance_type_id.color', store=True, string="Цвет")

    # --- СВЯЗАННЫЕ ПОЛЯ ---
    present = fields.Boolean('Present', related='attendance_type_id.present', store=True, readonly=True)
    excused = fields.Boolean('Absent Excused', related='attendance_type_id.excused', store=True, readonly=True)
    absent = fields.Boolean('Absent Unexcused', related='attendance_type_id.absent', store=True, readonly=True)
    late = fields.Boolean('Late', related='attendance_type_id.late', store=True, readonly=True)

    grade_1 = fields.Float('Оценка 1', aggregator="avg", default=False)
    grade_2 = fields.Float('Оценка 2', aggregator="avg", default=False)
    grade_3 = fields.Float('Оценка 3', aggregator="avg", default=False)

    # Вычисляемый средний балл строки
    grade_avg = fields.Float(
        string='Средний балл', 
        compute='_compute_grade_avg', 
        store=True, 
        aggregator="avg"
    )

    @api.depends('grade_1', 'grade_2', 'grade_3')
    def _compute_grade_avg(self):
        for rec in self:
            marks = [m for m in [rec.grade_1, rec.grade_2, rec.grade_3] if m and m > 0]            
            rec.grade_avg = sum(marks) / len(marks) if marks else False

    @api.onchange('attendance_type_id')
    def onchange_attendance_type(self):
        if self.attendance_type_id:
            self.present = self.attendance_type_id.present
            self.excused = self.attendance_type_id.excused
            self.absent = self.attendance_type_id.absent
            self.late = self.attendance_type_id.late

    # Перехватываем генерацию SQL для полей оценок.   
    @api.model
    def _field_to_sql(self, alias, fname, query=None, **kwargs):             
        sql_expression = super()._field_to_sql(alias, fname, query, **kwargs)        
        target_fields = ('grade_1', 'grade_2', 'grade_3', 'grade_avg')        
        if fname in target_fields:            
            return SQL("NULLIF(%s, 0)", sql_expression)            
        return sql_expression

    _sql_constraints = [
        ('unique_student',
         'unique(student_id,attendance_id,attendance_date)',
         'Student must be unique per Attendance.'),
    ]

    @api.model
    def get_aggregated_stats(self, domain):
        """ Универсальный метод агрегации Odoo (как в Пивоте) """
        # Считаем средние и суммы прямо в SQL
        # В Odoo 18 для 'grade_avg:avg' нужно, чтобы у поля был aggregator="avg"
        res = self.read_group(domain, 
            ['grade_avg:avg', 'present:sum', 'absent:sum', 'late:sum', 'excused:sum', 'id:count'], 
            []
        )
        if not res or not res[0]:
            return {'avg': 0.0, 'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'total': 0}
        
        data = res[0]
        return {
            'avg': round(data.get('grade_avg', 0.0) or 0.0, 2),
            'present': int(data.get('present', 0)),
            'absent': int(data.get('absent', 0)),
            'late': int(data.get('late', 0)),
            'excused': int(data.get('excused', 0)),
            'total': int(data.get('id_count', 0)),
        }

    @api.model
    def get_stats_from_lines(self, lines):
        """ Универсальный движок расчета: принимает RecordSet строк, возвращает словарь """
        res = {
            'avg': 0.0, 'total': len(lines),
            'present': 0, 'absent': 0, 'late': 0, 'excused': 0,
            'counts': {5: 0, 4: 0, 3: 0, 2: 0},
            'last_remark': "—", 'last_date': False,
            'html_summary': "",
            'types_detailed': {}, 
            'rate': 0.0,  # ДОБАВИЛИ ЭТОТ КЛЮЧ
        }
        if not lines: return res

        sorted_l = lines.sorted('attendance_date', reverse=True)
        res['last_date'] = sorted_l[0].attendance_date
        
        marks = []
        type_counts = {}

        for l in sorted_l:
            if l.present: res['present'] += 1
            if l.absent: res['absent'] += 1
            if l.late: res['late'] += 1
            if l.excused: res['excused'] += 1

            if l.attendance_type_id:
                name = l.attendance_type_id.name
                type_counts[name] = type_counts.get(name, 0) + 1

            for v in [l.grade_1, l.grade_2, l.grade_3]:
                if v and 2 <= v <= 5:
                    marks.append(v)
                    res['counts'][int(v)] += 1
            
            if l.remark and res['last_remark'] == "—":
                res['last_remark'] = l.remark

        # Математика
        res['avg'] = round(sum(marks) / len(marks), 2) if marks else 0.0
        # РАСЧЕТ ПРОЦЕНТА (теперь записывается в словарь)
        res['rate'] = round(res['present'] / res['total'] * 100, 2) if res['total'] > 0 else 0.0
        
        res['types_detailed'] = type_counts 

        # Генерация HTML
        html = []
        p_count = type_counts.get('Присутствует', 0)
        if p_count:
            html.append(f'<span class="badge rounded-pill me-2" style="background:#e8f5e9; color:#1b5e20; border:1px solid #c8e6c9; padding:4px 8px;">✅ Присутствовал: {p_count}</span>')
        for name, count in type_counts.items():
            color = "background:#fff3e0; color:#e65100;" if name in ['Прогул', 'Опоздал'] else "background:#f5f5f5; color:#666;"
            html.append(f'<span class="badge rounded-pill me-1" style="padding:4px 8px; border:1px solid #ddd; {color}">{name}: {count}</span>')
        res['html_summary'] = "".join(html)

        return res

    @api.model_create_multi
    def create(self, vals_list):        
        return super(OpAttendanceLine, self).create(vals_list)

    def write(self, vals):
        res = super(OpAttendanceLine, self).write(vals)
        trigger_fields = ['grade_1', 'grade_2', 'grade_3', 'attendance_type_id', 'remark']
        
        if any(f in vals for f in trigger_fields):            
            grades = self.env['op.subject.grades'].search([
                ('student_id', 'in', self.student_id.ids),
                ('subject_id', 'in', self.subject_id.ids)
            ])
            
            if grades:                
                grades.modified(['q1_line_ids', 'q2_line_ids', 'q3_line_ids', 'q4_line_ids'])                
                grades.action_force_recompute()
                
        return res    