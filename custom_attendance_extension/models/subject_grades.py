from odoo import models, fields


class OpSubjectGrades(models.Model):
    _inherit = "op.subject.grades"

    # Добавляем поле для тем уроков
    lesson_topics = fields.Text('Темы уроков')