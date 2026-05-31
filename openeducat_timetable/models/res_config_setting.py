from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    prevent_faculty_overlap = fields.Boolean(
        string="Запретить совмещение учителя",
        config_parameter='timetable.prevent_faculty_overlap')

    prevent_classroom_overlap = fields.Boolean(
        string="Запретить совмещение кабинета",
        config_parameter='timetable.prevent_classroom_overlap')

    prevent_batch_overlap = fields.Boolean(
        string="Запретить совмещение класса",
        config_parameter='timetable.prevent_batch_overlap')
