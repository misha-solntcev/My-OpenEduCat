from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    is_faculty_constraint = fields.Boolean(
        string="Faculty Constraint",
        config_parameter='timetable.is_faculty_constraint')
    
    is_classroom_constraint = fields.Boolean(
        string="Classroom Constraint",
        config_parameter='timetable.is_classroom_constraint')
    
    is_batch_constraint = fields.Boolean(
        string="Batch Constraint",
        config_parameter='timetable.is_batch_constraint')

    is_batch_and_subject_constraint = fields.Boolean(
        string="Batch and Subject Constraint",
        config_parameter='timetable.is_batch_and_subject_constraint')