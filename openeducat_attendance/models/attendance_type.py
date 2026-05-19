from odoo import fields, models


class OpAttendanceType(models.Model):
    _name = "op.attendance.type"
    _inherit = ["mail.thread"]
    _description = "Attendance Type"
    _order = "sequence, id"

    name = fields.Char(
        'Name', size=20, required=True, tracking=True)
    sequence = fields.Integer('Последовательность', default=10)
    color = fields.Integer('Цвет')
    active = fields.Boolean(default=True)

    present = fields.Boolean(
        'Present ?', tracking=True)
    excused = fields.Boolean(
        'Excused ?', tracking=True)
    absent = fields.Boolean('Absent', tracking=True)
    late = fields.Boolean('Late', tracking=True)
    
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
