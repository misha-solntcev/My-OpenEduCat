import base64
import re

from odoo import _, fields, http
from odoo.http import content_disposition, request
from odoo.tools import email_normalize

MAX_FILE_SIZE = 10 * 1024 * 1024
# Запас сверху на все файлы формы сразу: проверяем до чтения в память.
MAX_TOTAL_SIZE = 50 * 1024 * 1024
ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png', 'heic', 'heif'}
# Что принимает форма: обязательные СНИЛС и полис, свидетельство о
# рождении / паспорт ребёнка, скан паспорта заявителя + «другие».
DOC_TYPES = {
    'snils': 'СНИЛС (скан)',
    'policy': 'Медицинский полис',
    'birth_cert': 'Свидетельство о рождении',
    'child_passport': 'Паспорт ребёнка (скан)',
    'passport': 'Паспорт заявителя (скан)',
    'other': 'Другой документ',
}
# Все типы вложений анкеты (для показа уже загруженных файлов).
DOC_LABELS = dict(DOC_TYPES, consent='Согласие (скан)')
# Фото анкеты: не вложения, а Image-поля лида — при зачислении
# становятся аватарами ученика и родителя.
PHOTO_FIELDS = {
    'child_photo': 'Фото ученика',
    'parent_photo': 'Фото заявителя',
}
REQUIRED_FIELDS = (
    ('child_name', 'ФИО ребёнка'),
    ('child_birth_date', 'Дата рождения'),
    ('child_gender', 'Пол'),
    ('child_snils', 'СНИЛС ученика'),
    ('contact_name', 'ФИО заявителя'),
    ('relationship_id', 'Степень родства'),
    ('phone', 'Телефон'),
    ('email', 'Email'),
    ('parent_birth_date', 'Дата рождения заявителя'),
    ('parent_passport_number', 'Паспорт заявителя: серия и номер'),
    ('parent_passport_issued_by', 'Паспорт заявителя: кем выдан'),
    ('parent_passport_issue_date', 'Паспорт заявителя: дата выдачи'),
)
# Поля-даты: в форму и из формы ходят строкой ISO.
DATE_FIELDS = ('child_birth_date', 'parent_birth_date',
               'parent_passport_issue_date')
CONSENTS = (
    ('personal_data_consent', 'Согласие на обработку персональных данных'),
    ('consent_psych', 'Согласие на психологическое сопровождение'),
    ('consent_terms', 'Согласие с условиями договора'),
)


def _digits(value):
    return re.sub(r'\D', '', value or '')


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

        def date_value(key, default):
            if post is not None:
                return post.get(key) or ''
            return default and default.isoformat() or ''

        values = {
            'child_name': value('child_name', lead.child_name),
            'child_birth_date': date_value(
                'child_birth_date', lead.child_birth_date),
            'child_gender': value('child_gender', lead.child_gender),
            'child_email': value('child_email', lead.child_email),
            'child_phone': value('child_phone', lead.child_phone),
            'child_snils': value('child_snils', lead.child_snils),
            'child_inn': value('child_inn', lead.child_inn),
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
            'parent_birth_date': date_value(
                'parent_birth_date', lead.parent_birth_date),
            'parent_passport_number': value(
                'parent_passport_number', lead.parent_passport_number),
            'parent_passport_issued_by': value(
                'parent_passport_issued_by', lead.parent_passport_issued_by),
            'parent_passport_issue_date': date_value(
                'parent_passport_issue_date', lead.parent_passport_issue_date),
            'parent_passport_dept_code': value(
                'parent_passport_dept_code', lead.parent_passport_dept_code),
            'parent_address_reg': value(
                'parent_address_reg', lead.parent_address_reg),
            'parent_address_home': value(
                'parent_address_home', lead.parent_address_home),
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

    def _has_doc(self, documents, *doc_types):
        return any(attachment.rost_doc_type in doc_types
                   for attachment in documents)

    def _render(self, token, lead, values=None, errors=None, success=None):
        if success is None:
            success = (bool(lead.zayavlenie_filled_date)
                       and not request.params.get('edit'))
        documents = request.env['ir.attachment'].sudo().search(
            lead._zayavlenie_attachment_domain())
        has_doc = {doc_type: self._has_doc(documents, doc_type)
                   for doc_type in DOC_TYPES}
        # Свидетельство о рождении и паспорт ребёнка взаимозаменяемы:
        # нужен один из двух документов.
        has_doc['child_id'] = self._has_doc(
            documents, 'birth_cert', 'child_passport')
        return request.render('rost_school_billing.zayavlenie_page', {
            'token': token,
            'lead': lead,
            'success': success,
            'values': values or self._values(lead),
            'errors': errors or [],
            'documents': self._documents(lead, token),
            'relationships': request.env['op.parent.relationship'].sudo(
            ).search([]),
            'has_doc': has_doc,
            'has_photo': {
                'child': bool(lead.child_photo),
                'parent': bool(lead.parent_photo),
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

    def _read_photos(self, errors):
        """Фото из анкеты: {поле лида: base64} — Image-поля, не вложения."""
        photos = {}
        for field_name, label in PHOTO_FIELDS.items():
            upload = request.httprequest.files.get(field_name)
            if not upload or not upload.filename:
                continue
            ext = (upload.filename.rsplit('.', 1)[-1].lower()
                   if '.' in upload.filename else '')
            if ext not in ALLOWED_EXT:
                errors.append(_(
                    '«%s»: недопустимый формат файла. Можно PDF, JPG, '
                    'PNG или HEIC.') % label)
                continue
            data = upload.read()
            if len(data) > MAX_FILE_SIZE:
                errors.append(_('«%s» больше 10 МБ.') % label)
                continue
            photos[field_name] = base64.b64encode(data)
        return photos

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

    @http.route('/zayavlenie/<string:token>/photo/<string:kind>', type='http',
                auth='public', sitemap=False)
    def zayavlenie_photo(self, token, kind, **kw):
        """Превью фото из анкеты (см. zayavlenie_document)."""
        lead = self._get_lead(token)
        if not lead or kind not in ('child', 'parent'):
            return request.not_found()
        data = (lead.child_photo if kind == 'child'
                else lead.parent_photo)
        if not data:
            return request.not_found()
        return request.make_response(
            base64.b64decode(data),
            [('Content-Type', 'image/jpeg'),
             ('Cache-Control', 'private, max-age=300')])

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

        dates = {}
        for key in DATE_FIELDS:
            label = dict(REQUIRED_FIELDS).get(key, key)
            raw = values.get(key)
            if not raw:
                dates[key] = False
                continue
            try:
                dates[key] = fields.Date.to_date(raw)
            except (TypeError, ValueError):
                errors.append(_('«%s» указана неверно.') % label)
                dates[key] = False
        today = fields.Date.context_today(lead)
        for key in ('child_birth_date', 'parent_birth_date'):
            if dates.get(key) and dates[key] > today:
                errors.append(_(
                    '«Дата рождения» не может быть в будущем.'))
        if dates.get('parent_passport_issue_date') \
                and dates['parent_passport_issue_date'] > today:
            errors.append(_(
                '«Паспорт заявителя: дата выдачи» не может быть в будущем.'))
        if dates.get('child_birth_date') \
                and dates.get('parent_birth_date') \
                and dates['parent_birth_date'] >= dates['child_birth_date']:
            errors.append(_(
                'Дата рождения заявителя должна быть раньше даты рождения '
                'ребёнка.'))

        snils = _digits(values.get('child_snils'))
        if snils and len(snils) != 11:
            errors.append(_(
                'СНИЛС ученика — 11 цифр (например 123-456-789 00).'))
        inn = _digits(values.get('child_inn'))
        if inn and len(inn) not in (10, 12):
            errors.append(_('ИНН ученика — 10 или 12 цифр.'))

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
        if values.get('child_email'):
            if not email_normalize(values['child_email']):
                errors.append(_('Укажите корректный email ученика.'))
            elif email_normalize(values['child_email']) \
                    == email_normalize(values.get('email')):
                errors.append(_(
                    'Email ученика совпадает с email заявителя: аккаунт '
                    'ученика не создать. Оставьте поле пустым или укажите '
                    'второй адрес.'))
        for key, label in CONSENTS:
            if not values.get(key):
                errors.append(_('Отметьте «%s».') % label)

        files = self._read_uploads(errors)
        photos = self._read_photos(errors)
        existing = request.env['ir.attachment'].sudo().search(
            lead._zayavlenie_attachment_domain())
        for doc_type, label in (
                ('snils', 'СНИЛС (скан)'),
                ('policy', 'Медицинский полис'),
                ('passport', 'Паспорт заявителя (скан)')):
            if not files.get(doc_type) and not self._has_doc(
                    existing, doc_type):
                errors.append(_('Приложите файл «%s».') % label)
        child_id_uploaded = bool(files.get('birth_cert')
                                 or files.get('child_passport'))
        if not child_id_uploaded and not self._has_doc(
                existing, 'birth_cert', 'child_passport'):
            errors.append(_(
                'Приложите свидетельство о рождении или паспорт ребёнка.'))

        if errors:
            return self._render(
                token, lead, values=values, errors=errors, success=False)

        lead.write({
            'child_name': values['child_name'].strip(),
            'child_birth_date': dates['child_birth_date'],
            'child_gender': values['child_gender'],
            'child_email': values['child_email'].strip(),
            'child_phone': values['child_phone'].strip(),
            'child_snils': values['child_snils'].strip(),
            'child_inn': values['child_inn'].strip(),
            'child_current_school': values['child_current_school'].strip(),
            'child_interests': values['child_interests'].strip(),
            'child_medical': values['child_medical'].strip(),
            'contact_name': values['contact_name'].strip(),
            'phone': values['phone'].strip(),
            'email_from': values['email'].strip(),
            'parent_birth_date': dates['parent_birth_date'],
            'parent_passport_number': values['parent_passport_number'].strip(),
            'parent_passport_issued_by': values[
                'parent_passport_issued_by'].strip(),
            'parent_passport_issue_date': dates['parent_passport_issue_date'],
            'parent_passport_dept_code': values[
                'parent_passport_dept_code'].strip(),
            'parent_address_reg': values['parent_address_reg'].strip(),
            'parent_address_home': values['parent_address_home'].strip(),
            # Адрес семьи для контакта при приёмке: фактический, если он
            # не заполнен — регистрации (раньше это поле формы
            # «Адрес проживания», теперь вводится как адрес заявителя).
            'child_address': (values['parent_address_home'].strip()
                              or values['parent_address_reg'].strip()),
            'description': values['description'].strip(),
            'child_parent_relationship_id': relationship_id,
            'personal_data_consent': True,
            'consent_psych': True,
            'consent_terms': True,
            'zayavlenie_filled_date': fields.Datetime.now(),
        })
        if photos:
            lead.write(photos)
        # Телефон родителя — в Mobile контакта заявителя (поле, которое
        # школа ведёт и требует в карточке родителя). Запись в lead.phone
        # выше сама положит номер и в Phone через CRM-inverse — это
        # нативное поведение crm.lead, не наша синхронизация.
        # Телефон ребёнка остаётся на child_phone и уезжает в Mobile
        # контакта ученика при зачислении.
        applicant = lead.partner_id
        parent_phone = values['phone'].strip()
        if applicant and parent_phone \
                and (applicant.mobile or '').strip() != parent_phone:
            applicant.write({'mobile': parent_phone})
        # Анкета может прийти после зачисления — тогда данные ребёнка
        # (телефон, СНИЛС/ИНН, фото) переносим в карточку сами.
        self._sync_enrolled_student(lead, values)
        self._save_uploads(lead, files)
        return request.redirect('/zayavlenie/%s' % token)

    def _enrolled_student(self, lead):
        """Ученик, если лид уже дошёл до зачисления (заказ → приёмка)."""
        env = request.env
        order = env['sale.order'].sudo().search(
            [('opportunity_id', '=', lead.id)], limit=1)
        if not order:
            return env['op.student']
        admission = env['op.admission'].sudo().search(
            [('sale_order_id', '=', order.id),
             ('student_id', '!=', False)], limit=1)
        return admission.student_id

    def _sync_enrolled_student(self, lead, values):
        """Анкету могут заполнить ПОСЛЕ зачисления (семья получила ссылку
        позже). Данные ребёнка тогда некому перенести: enroll_student уже
        прошёл, get_student_vals больше не вызывается. Переносим сами:
        телефон → Mobile контакта ученика, СНИЛС/ИНН и фото — в карточку.
        Пустые значения не затирают заполненные."""
        student = self._enrolled_student(lead)
        if not student:
            return student
        vals = {}
        child_phone = values['child_phone'].strip()
        if child_phone and (student.partner_id.mobile or '') != child_phone:
            vals['mobile'] = child_phone
        snils = values['child_snils'].strip()
        if snils and (student.snils or '') != snils:
            vals['snils'] = snils
        inn = values['child_inn'].strip()
        if inn and (student.inn or '') != inn:
            vals['inn'] = inn
        if lead.child_photo and not student.image_1920:
            vals['image_1920'] = lead.child_photo
        if vals:
            student.write(vals)
        parent = student.parent_ids[:1]
        if lead.parent_photo and parent.partner_id \
                and not parent.partner_id.image_1920:
            parent.partner_id.image_1920 = lead.parent_photo
        return student

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
