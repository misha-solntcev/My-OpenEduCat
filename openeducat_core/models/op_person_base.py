from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class OpPersonBase(models.AbstractModel):
    _name = "op.person.base"
    _description = "Base Person Model"

    first_name = fields.Char('First Name', required=True, translate=True)
    middle_name = fields.Char('Middle Name', translate=True)
    last_name = fields.Char('Last Name', required=True, translate=True)
    birth_date = fields.Date('Birth Date')
    gender = fields.Selection([
        ('m', 'Male'),
        ('f', 'Female'),
        ('o', 'Other')
    ], 'Gender', required=True, default='m')
    blood_group = fields.Selection([
        ('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
        ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve')
    ], string='Blood Group')
    
    nationality = fields.Many2one('res.country', 'Nationality')
    emergency_contact = fields.Many2one('res.partner', 'Emergency Contact')
    visa_info = fields.Char('Visa Info', size=64)
    id_number = fields.Char('ID Card Number', size=64)

    @api.onchange('first_name', 'middle_name', 'last_name')
    def _onchange_name(self):
        """Единый стандарт формирования имени: Фамилия Имя Отчество"""
        names = [
            self.last_name or '',
            self.first_name or '',
            self.middle_name or ''
        ]
        self.name = " ".join([n.strip() for n in names if n]).strip()

    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
            if record.birth_date and record.birth_date > fields.Date.today():
                raise ValidationError(_("Birth Date can't be greater than current date!"))