import secrets
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models

TOKEN_DAYS = 7


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    child_parent_relationship_id = fields.Many2one(
        'op.parent.relationship', 'Степень родства заявителя',
        help='Кем заявитель приходится ребёнку. Выпадающий список из '
             'справочника (как «класс»); при создании приёмки уезжает '
             'в op.parent автоматически.')
    child_name = fields.Char('ФИО ребёнка')
    child_email = fields.Char(
        'Email ученика',
        help='Собственная почта ребёнка (не родителя!). Пусто — при '
             'зачислении будет один аккаунт, родительский.')
    child_birth_date = fields.Date('Дата рождения ребёнка')
    child_gender = fields.Selection([
        ('m', 'Мужской'),
        ('f', 'Женский'),
    ], 'Пол ребёнка')
    child_course_id = fields.Many2one(
        'op.course', 'Класс',
        help='Подсказка для КП; окончательно класс подтверждается в приёмке.')
    child_current_school = fields.Char('Текущая школа')
    child_interests = fields.Text('Интересы и увлечения')
    child_medical = fields.Text(
        'Медицинские особенности',
        help='Указываются добровольно (анкета сайта).')
    child_address = fields.Char(
        'Адрес проживания (семья)',
        help='Записывается в адрес родителя при создании приёмки.')
    personal_data_consent = fields.Boolean(
        'Согласие на обработку персональных данных')
    existing_student_id = fields.Many2one(
        'op.student', 'Уже учится (ученик)',
        help='Заполните, если ребёнок уже числится в школе: '
             'приёмка привяжется к нему, а не создаст нового.')

    # --- Анкета-заявление по персональной ссылке ---
    # Анкета нужна для сбора данных и документов к договору, поэтому
    # живёт на лиде: он существует на всех стадиях воронки, а заказ и
    # приёмка лишь ссылаются на него (файлы не дублируются).
    zayavlenie_token = fields.Char(
        'Токен анкеты', copy=False, index=True,
        help='Секрет из ссылки /zayavlenie/<token>.')
    zayavlenie_sent_date = fields.Datetime(
        'Ссылка выдана', copy=False, readonly=True)
    zayavlenie_filled_date = fields.Datetime(
        'Анкета заполнена', copy=False, readonly=True)
    zayavlenie_url = fields.Char(
        'Ссылка на анкету', compute='_compute_zayavlenie_url')
    zayavlenie_state = fields.Selection([
        ('none', 'Нет ссылки'),
        ('sent', 'Ссылка выдана'),
        ('filled', 'Анкета заполнена'),
        ('expired', 'Срок ссылки истёк'),
    ], 'Статус анкеты', compute='_compute_zayavlenie_state')
    consent_psych = fields.Boolean(
        'Согласие на психологическое сопровождение')
    consent_terms = fields.Boolean(
        'Согласие с условиями договора')

    @api.depends('zayavlenie_token')
    def _compute_zayavlenie_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        for lead in self:
            lead.zayavlenie_url = (
                '%s/zayavlenie/%s' % (base_url, lead.zayavlenie_token)
                if lead.zayavlenie_token else False)

    @api.depends('zayavlenie_token', 'zayavlenie_sent_date',
                 'zayavlenie_filled_date')
    def _compute_zayavlenie_state(self):
        for lead in self:
            if lead.zayavlenie_filled_date:
                lead.zayavlenie_state = 'filled'
            elif not lead.zayavlenie_token:
                lead.zayavlenie_state = 'none'
            elif lead._zayavlenie_expired():
                lead.zayavlenie_state = 'expired'
            else:
                lead.zayavlenie_state = 'sent'

    def _zayavlenie_attachment_domain(self):
        """Вложения анкеты: все файлы, загруженные родителем через форму
        (после зачисления они разъезжаются по ученику и родителю)."""
        self.ensure_one()
        return [
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
            ('rost_doc_type', 'in', ('snils', 'policy', 'birth_cert',
                                     'passport', 'consent', 'other')),
        ]

    def _zayavlenie_expired(self):
        self.ensure_one()
        if not self.zayavlenie_sent_date:
            return False
        deadline = self.zayavlenie_sent_date + timedelta(days=TOKEN_DAYS)
        return fields.Datetime.now() > deadline

    def _zayavlenie_is_valid(self):
        """Ссылка жива: не истекла или анкета уже заполнена."""
        self.ensure_one()
        if not self.zayavlenie_token:
            return False
        return bool(self.zayavlenie_filled_date) or not self._zayavlenie_expired()

    def _zayavlenie_ensure_token(self, regenerate=False):
        self.ensure_one()
        if regenerate or not self.zayavlenie_token:
            self.write({
                'zayavlenie_token': secrets.token_urlsafe(24),
                'zayavlenie_sent_date': fields.Datetime.now(),
            })
        return self.zayavlenie_url

    def action_zayavlenie_send(self):
        """Выдать ссылку (если нужно) и открыть письмо родителю."""
        self.ensure_one()
        url = self._zayavlenie_ensure_token()
        body = Markup(
            '<p>Здравствуйте!</p>'
            '<p>Чтобы подать заявление, заполните анкету по ссылке: '
            '<a href="%(url)s">%(url)s</a></p>'
            '<p>К анкете нужно приложить СНИЛС и медицинский полис. '
            'Ссылка действует %(days)s дней.</p>'
        ) % {'url': url, 'days': TOKEN_DAYS}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Отправить анкету'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'crm.lead',
                'default_res_ids': self.ids,
                'default_composition_mode': 'comment',
                'default_subject': _('Анкета для поступления'),
                'default_body': body,
                'default_partner_ids': [(6, 0, self.partner_id.ids)],
            },
        }

    def action_open_zayavlenie_form(self):
        """Открыть анкету на сайте — как её видит и заполняет родитель."""
        self.ensure_one()
        if not self.zayavlenie_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Ссылка не создана'),
                    'message': _('Анкета ещё не отправлялась: создайте '
                                 'ссылку кнопкой «Отправить анкету» в '
                                 'шапке лида.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'url': self.zayavlenie_url,
            'target': 'new',
        }

    def action_zayavlenie_new_link(self):
        """Перевыпустить ссылку (истекла или ушла не туда)."""
        self.ensure_one()
        self._zayavlenie_ensure_token(regenerate=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Ссылка обновлена'),
                'message': self.zayavlenie_url,
                'type': 'success',
                'sticky': False,
            },
        }
