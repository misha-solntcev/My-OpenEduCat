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

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpSubjectRegistration(models.Model):
    _name = "op.subject.registration"
    _description = "Subject Registration Details"
    _inherit = ["mail.thread"]

    name = fields.Char('Name', readonly=True, default='New')
    student_id = fields.Many2one('op.student', 'Student',
                                 tracking=True)
    course_id = fields.Many2one('op.course', 'Course', required=True,
                                tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch',
                               tracking=True)
    compulsory_subject_ids = fields.Many2many(
        'op.subject', 'subject_compulsory_rel',
        'register_id', 'subject_id', string="Compulsory Subjects")
    # readonly снят: набор обязательных предметов у каждого ученика свой
    # (английский А/Б, профильная математика), и задать его вручную —
    # единственный способ. Раньше поле было readonly=True, заполнить его
    # можно было только кнопкой get_subjects, которая брала предметы курса
    # и подтирала индивидуальный набор. Фактическая блокировка перенесена
    # во вьюху: редактируемо только в состоянии draft.
    elective_subject_ids = fields.Many2many(
        'op.subject', string="Elective Subjects")
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft', string='State', copy=False,
        tracking=True)
    max_unit_load = fields.Float('Maximum Unit Load',
                                 tracking=True)
    min_unit_load = fields.Float('Minimum Unit Load',
                                 tracking=True)
    is_read = fields.Boolean(string="Read?", default=False)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    def action_reset_draft(self):
        self.state = 'draft'

    def action_reject(self):
        self.state = 'rejected'

    def action_approve(self):
        for record in self:
            subject_ids = []
            for sub in record.compulsory_subject_ids:
                subject_ids.append(sub.id)
            for sub in record.elective_subject_ids:
                subject_ids.append(sub.id)
            # Зачисление ищем по (ученик, курс, ПАРАЛЛЕЛЬ) — курс общий
            # для нескольких лет, и поиск без batch_id + limit=1 писал бы
            # предметы в зачисление ПРОШЛОГО года, тихо портя историю.
            course_id = record._find_enrollment()
            if course_id:
                # Элективные предметы, уже записанные в зачисление, не
                # теряем: Approve не должен стирать выбор ученика, если
                # в регистрации их не перечислили. Обязательные — наоборот,
                # берём ровно те, что указаны в регистрации.
                electives = course_id.subject_ids.filtered(
                    lambda s: s.subject_type == 'elective'
                )
                merged = list(set(subject_ids) | set(electives.ids))
                course_id.write({
                    'subject_ids': [(6, 0, merged)]
                })
                record.state = 'approved'
            else:
                # Зачисления в этой параллели нет — писать некуда. Раньше
                # поиск шёл без параллели и молча писал в зачисление
                # ДРУГОГО года. Лучше явная ошибка.
                raise ValidationError(_(
                    "Student %s is not enrolled in batch %s. "
                    "Check the batch of this registration, or enrol "
                    "the student in 'Student Info → Course Details' first."
                ) % (record.student_id.name or '', record.batch_id.name or ''))

    def action_submitted(self):
        self.state = 'submitted'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'op.subject.registration') or '/'
        return super(OpSubjectRegistration, self).create(vals_list)

    def _find_enrollment(self):
        """Зачисление ученика для этой регистрации.

        Ищем по (ученик, курс, ПАРАЛЛЕЛЬ): курс в OpenEduCat общий для
        нескольких лет (курс «6 класс» — и для 6А 2025/2026, и для
        6А 2026/2027), поэтому поиск только по (ученик, курс) без
        параллели брал бы зачисление ПРОШЛОГО года и молча портило
        историю. Если параллель в регистрации не совпала с зачислением
        (бывает при переносе класса), ищем ту же параллель по названию.

        Если параллель указана, но зачисления в ней нет — ВОЗВРАЩАЕМ
        ПУСТО: подставлять зачисление другой параллели нельзя, Approve
        записал бы предметы не тому ученику (или тому же, но в чужом
        году). Лучше явная ошибка, чем тихая порча.

        state НЕ фильтруем: у переведённых учеников зачисление в состоянии
        finished, и они тоже должны получить свой индивидуальный набор
        предметов, а не предметы курса.
        """
        self.ensure_one()
        StudentCourse = self.env['op.student.course']
        if self.batch_id:
            enrollment = StudentCourse.search([
                ('student_id', '=', self.student_id.id),
                ('course_id', '=', self.course_id.id),
                ('batch_id', '=', self.batch_id.id),
            ], limit=1)
            if enrollment:
                return enrollment
            # Та же параллель по названию (регистрация могла быть создана
            # для одноимённого класса другого года).
            batch = self.env['op.batch'].search([
                ('name', '=', self.batch_id.name),
            ], limit=1)
            if batch:
                enrollment = StudentCourse.search([
                    ('student_id', '=', self.student_id.id),
                    ('course_id', '=', self.course_id.id),
                    ('batch_id', '=', batch.id),
                ], limit=1)
                if enrollment:
                    return enrollment
            return self.env['op.student.course']
        # Параллель не указана — ищем единственное зачисление по курсу.
        return StudentCourse.search([
            ('student_id', '=', self.student_id.id),
            ('course_id', '=', self.course_id.id),
        ], limit=1)

    def get_subjects(self):
        for record in self:
            enrollment = record._find_enrollment()
            if enrollment and enrollment.subject_ids:
                # Индивидуальный набор ученика (англ. А/Б, профиль).
                record.compulsory_subject_ids = [
                    (6, 0, enrollment.subject_ids.ids)
                ]
                continue
            # Зачисление не найдено или в нём нет предметов — первичное
            # заполнение предметами курса. Дальше завуч дорабатывает
            # набор вручную (поле редактируемо в состоянии draft).
            subject_ids = []
            if record.course_id and record.course_id.subject_ids:
                for subject in record.course_id.subject_ids:
                    if subject.subject_type == 'compulsory':
                        subject_ids.append(subject.id)
            record.compulsory_subject_ids = [(6, 0, subject_ids)]
