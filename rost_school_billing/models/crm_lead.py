from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    child_name = fields.Char('ФИО ребёнка')
    child_birth_date = fields.Date('Дата рождения ребёнка')
    child_gender = fields.Selection([
        ('m', 'Мужской'),
        ('f', 'Женский'),
    ], 'Пол ребёнка')
    child_course_id = fields.Many2one(
        'op.course', 'Планируемый класс',
        help='Подсказка для КП; окончательно класс подтверждается в приёмке.')
    child_current_school = fields.Char('Текущая школа')
    child_interests = fields.Text('Интересы и увлечения')
    child_address = fields.Char(
        'Адрес проживания (семья)',
        help='Записывается в адрес родителя при создании приёмки.')
    personal_data_consent = fields.Boolean(
        'Согласие на обработку персональных данных')
    existing_student_id = fields.Many2one(
        'op.student', 'Уже учится (ученик)',
        help='Заполните, если ребёнок уже числится в школе: '
             'приёмка привяжется к нему, а не создаст нового.')
