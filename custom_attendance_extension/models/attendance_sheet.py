from odoo import models, fields


class OpAttendanceSheet(models.Model):
    _inherit = "op.attendance.sheet"

    # Добавляем поле для темы урока
    lesson_topic = fields.Char('Тема урока', size=256)