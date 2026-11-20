import base64

from odoo import _, fields, http
from odoo.http import content_disposition, request
from odoo.tools import email_normalize

MAX_FILE_SIZE = 10 * 1024 * 1024
# Запас сверху на все файлы формы сразу: проверяем до чтения в память.
MAX_TOTAL_SIZE = 50 * 1024 * 1024
ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png', 'heic', 'heif'}
# Что принимает форма: обязательные СНИЛС и полис + «другие».
DOC_TYPES = {
    'snils': 'СНИЛС',
    'policy': 'Медицинский полис',
    'other': 'Другой документ',
}
# Все типы вложений анкеты (для показа уже загруженных файлов).
DOC_LABELS = dict(DOC_TYPES,
                  birth_cert='Свидетельство о рождении',
                  passport='Паспорт (скан)',
                  consent='Согласие (скан)')
REQUIRED_FIELDS = (
    ('child_name', 'ФИО ребёнка'),
    ('child_birth_date', 'Дата рождения'),
    ('child_gender', 'Пол'),
    ('contact_name', 'ФИО заявителя'),
    ('relationship_id', 'Степень родства'),
    ('phone', 'Телефон'),
    ('email', 'Email'),
)
CONSENTS = (
    ('personal_data_consent', 'Согласие на обработку персональных данных'),
    ('consent_psych', 'Согласие на психологическое сопровождение'),
    ('consent_terms', 'Согласие с условиями договора'),
)


class ZayavlenieController(http.Controller):

    # --- helpers ---

    def _get_lead(self, token):
        lead = request.env['crm.lead'].sudo().search(
            [('zayavlenie_token', '=', token)], limit=1)
        if lead and lead._zayavlenie_is_valid():
            return lead
        return request.env['crm.lead']

    def _values(self, lead, post=None):
        def value(key, default):
            if post is not None:
                return post.get(key) or ''
            return default if default not in (None, False) else ''

        values = {
            'child_name': value('child_name', lead.child_name),
            'child_birth_date': value(
                'child_birth_date',
                lead.child_birth_date and lead.child_birth_date.isoformat()),
            'child_gender': value('child_gender', lead.child_gender),
            'child_current_school': value(
                'child_current_school', lead.child_current_school),
            'child_interests': value(
                'child_interests', lead.child_interests),
            'child_medical': value('child_medical', lead.child_medical),
            'contact_name': value(
                'contact_name', lead.contact_name or lead.partner_id.name),
            'relationship_id': value(
                'relationship_id',
                lead.child_parent_relationship_id.id or ''),
            'phone': value('phone', lead.phone),
            'email': value(
                'email', lead.email_from or lead.partner_id.email),
            'child_address': value('child_address', lead.child_address),
            'description': value('description', lead.description),
        }
        for key, _label in CONSENTS:
            if post is not None:
                values[key] = bool(post.get(key))
            else:
                values[key] = bool(lead[key])
        return values

    def _documents(self, lead, token):
        # Файлы отдаём своим роутом по токену: /web/content требует
        # внутреннего пользователя, анониму он ответил бы 403.
        return [{
            'name': attachment.name,
            'url': '/zayavlenie/%s/doc/%s' % (token, attachment.id),
            'label': DOC_LABELS.get(attachment.rost_doc_type, ''),
        } for attachment in request.env['ir.attachment'].sudo().search(
            lead._zayavlenie_attachment_domain())]

    def _render(self, token, lead, values=None, errors=None, success=None):
        if success is None:
            success = (bool(lead.zayavlenie_filled_date)
                       and not request.params.get('edit'))
        documents = request.env['ir.attachment'].sudo().search(
            lead._zayavlenie_attachment_domain())
        return request.render('rost_school_billing.zayavlenie_page', {
            'token': token,
            'lead': lead,
            'success': success,
            'values': values or self._values(lead),
            'errors': errors or [],
            'documents': self._documents(lead, token),
            'relationships': request.env['op.parent.relationship'].sudo(
            ).search([]),
            'has_doc': {
                'snils': any(a.rost_doc_type == 'snils' for a in documents),
                'policy': any(a.rost_doc_type == 'policy' for a in documents),
            },
        })

    def _read_uploads(self, errors):
        """Собрать файлы из POST: {тип: [(имя, mimetype, данные)]}."""
        if (request.httprequest.content_length or 0) > MAX_TOTAL_SIZE:
            errors.append(_(
                'Запрос слишком большой: суммарно до 50 МБ на все файлы.'))
            return {}
        files = {}
        for doc_type, label in DOC_TYPES.items():
            uploads = request.httprequest.files.getlist(doc_type)
            if doc_type != 'other':
                uploads = uploads[:1]
            files[doc_type] = []
            for upload in uploads:
                if not upload or not upload.filename:
                    continue
                ext = (upload.filename.rsplit('.', 1)[-1].lower()
                       if '.' in upload.filename else '')
                if ext not in ALLOWED_EXT:
                    errors.append(_(
                        'Файл «%s»: недопустимый формат. Можно PDF, JPG, '
                        'PNG или HEIC.') % upload.filename)
                    continue
                data = upload.read()
                if len(data) > MAX_FILE_SIZE:
                    errors.append(_(
                        'Файл «%s» больше 10 МБ.') % upload.filename)
                    continue
                files[doc_type].append(
                    (upload.filename, upload.mimetype, data))
        return files

    # --- routes ---

    @http.route('/zayavlenie/<string:token>', type='http', auth='public',
                website=True, sitemap=False)
    def zayavlenie_page(self, token, **kw):
        lead = self._get_lead(token)
        if not lead:
            return request.render(
                'rost_school_billing.zayavlenie_invalid', {})
        return self._render(token, lead)

    @http.route('/zayavlenie/<string:token>/doc/<int:doc_id>', type='http',
                auth='public', sitemap=False)
    def zayavlenie_document(self, token, doc_id, **kw):
        """Отдать файл анкеты: ядро не даёт анониму читать ir.attachment
        (/web/content), поэтому скачивание идёт по проверенному токену и
        только для вложений этого лида."""
        lead = self._get_lead(token)
        if not lead:
            return request.render(
                'rost_school_billing.zayavlenie_invalid', {})
        attachment = request.env['ir.attachment'].sudo().search(
            lead._zayavlenie_attachment_domain() + [('id', '=', doc_id)],
            limit=1)
        if not attachment:
            return request.not_found()
        data = base64.b64decode(attachment.datas)
        headers = [
            ('Content-Type', attachment.mimetype
             or 'application/octet-stream'),
            ('Content-Disposition', content_disposition(attachment.name)),
        ]
        return request.make_response(data, headers)

    @http.route('/zayavlenie/<string:token>/submit', type='http',
                auth='public', website=True, methods=['POST'])
    def zayavlenie_submit(self, token, **post):
        lead = self._get_lead(token)
        if not lead:
            return request.render(
                'rost_school_billing.zayavlenie_invalid', {})
        values = self._values(lead, post)
        errors = []
        for key, label in REQUIRED_FIELDS:
            if not str(values.get(key) or '').strip():
                errors.append(_('Заполните поле «%s».') % label)
        if values.get('child_gender') not in ('m', 'f'):
            errors.append(_('Укажите пол ребёнка.'))
        birth_date = False
        if values.get('child_birth_date'):
            try:
                birth_date = fields.Date.to_date(values['child_birth_date'])
            except (TypeError, ValueError):
                errors.append(_('Дата рождения указана неверно.'))
        relationship_id = False
        if values.get('relationship_id'):
            try:
                relationship_id = int(values['relationship_id'])
            except (TypeError, ValueError):
                pass
            if not relationship_id or not request.env[
                    'op.parent.relationship'].sudo().browse(
                    relationship_id).exists():
                errors.append(_('Выберите степень родства из списка.'))
        if values.get('email') and not email_normalize(values['email']):
            errors.append(_('Укажите корректный email.'))
        for key, label in CONSENTS:
            if not values.get(key):
                errors.append(_('Отметьте «%s».') % label)

        files = self._read_uploads(errors)
        existing = request.env['ir.attachment'].sudo().search(
            lead._zayavlenie_attachment_domain())
        for doc_type, label in (('snils', 'СНИЛС'),
                                ('policy', 'Медицинский полис')):
            if not files.get(doc_type) and not existing.filtered(
                    lambda a, t=doc_type: a.rost_doc_type == t):
                errors.append(_('Приложите файл «%s».') % label)

        if errors:
            return self._render(
                token, lead, values=values, errors=errors, success=False)

        lead.write({
            'child_name': values['child_name'].strip(),
            'child_birth_date': birth_date,
            'child_gender': values['child_gender'],
            'child_current_school': values['child_current_school'].strip(),
            'child_interests': values['child_interests'].strip(),
            'child_medical': values['child_medical'].strip(),
            'contact_name': values['contact_name'].strip(),
            'phone': values['phone'].strip(),
            'email_from': values['email'].strip(),
            'child_address': values['child_address'].strip(),
            'description': values['description'].strip(),
            'child_parent_relationship_id': relationship_id,
            'personal_data_consent': True,
            'consent_psych': True,
            'consent_terms': True,
            'zayavlenie_filled_date': fields.Datetime.now(),
        })
        self._save_uploads(lead, files)
        return request.redirect('/zayavlenie/%s' % token)

    def _save_uploads(self, lead, files):
        Attachment = request.env['ir.attachment'].sudo()
        for doc_type, uploads in files.items():
            if not uploads:
                continue
            if doc_type != 'other':
                # одиночный документ: повторная загрузка заменяет файл
                Attachment.search([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', lead.id),
                    ('rost_doc_type', '=', doc_type),
                ]).unlink()
            for filename, mimetype, data in uploads:
                Attachment.create({
                    'name': filename,
                    'datas': base64.b64encode(data),
                    'res_model': 'crm.lead',
                    'res_id': lead.id,
                    'mimetype': mimetype or 'application/octet-stream',
                    'rost_doc_type': doc_type,
                })
