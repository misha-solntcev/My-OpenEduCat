# -*- coding: utf-8 -*-
"""Реестр шаблонов документов школы.

Новый вид документа (договор, допсоглашение, согласие на ПДн,
заявление о приёме...) = новая запись реестра + .docx с {{tokens}}.
Код и деплой не нужны.
"""
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

DOC_MODELS = [
    ('contract.contract', 'Подписка (договор)'),
    ('op.student', 'Ученик'),
    ('op.admission', 'Приёмка'),
]


class RostDocTemplate(models.Model):
    _name = 'rost.doc.template'
    _description = 'Шаблон документа школы'
    _order = 'sequence, name'
    _rec_name = 'name'

    sequence = fields.Integer('Порядок', default=10)
    name = fields.Char('Название', required=True,
                       help="«Договор об образовании», «ДопСоглашение»...")
    code = fields.Char('Код', required=True,
                       help="Латиницей/цифрами, уникально: contract, "
                            "agreement, consent_pd...")
    res_model = fields.Selection(
        DOC_MODELS, 'Доступен для', required=True,
        default='contract.contract',
        help="На записях какой модели появляется шаблон в мастере "
             "генерации.")
    template_file = fields.Binary(
        'Шаблон (.docx)', required=True, attachment=True,
        groups='base.group_system',
        help="Word-файл с токенами {{...}}. Контекст токенов — см. "
             "описание в карточке шаблона.")
    template_filename = fields.Char('Имя файла шаблона')
    filename_pattern = fields.Char(
        'Шаблон имени файла',
        help="Имя создаваемого файла. Плейсхолдеры — контекст токенов, "
             "например: «Договор {contract_number_full} "
             "{student_name}.docx». Пусто — «Название — запись.docx».")
    active = fields.Boolean('Активный', default=True)
    note = fields.Text(
        'Описание / доступные токены',
        help="Памятка секретарю и админу: какие токены использует "
             "шаблон и что заполнять в карточках.")

    @api.constrains('code')
    def _check_code_uniq(self):
        for rec in self:
            if self.search_count([
                    ('code', '=', rec.code),
                    ('id', '!=', rec.id)]):
                raise ValidationError(_(
                    'Код шаблона «%s» уже используется.') % rec.code)

    @api.constrains('template_file')
    def _check_template_file(self):
        for rec in self:
            if not rec.template_file:
                continue
            import base64
            from .doc_engine import render_docx
            data = base64.b64decode(rec.template_file)
            if not data.startswith(b'PK'):
                raise ValidationError(_(
                    'Шаблон «%s»: ожидается файл .docx (zip-контейнер).'
                ) % rec.name)

    def _rost_filename(self, record, context):
        """Имя файла документа: шаблон имени или «Название — запись»."""
        self.ensure_one()
        pattern = self.filename_pattern
        if pattern:
            class _Safe(dict):
                def __missing__(self, key):
                    return '{%s}' % key
            name = pattern.format_map(_Safe(**context))
        else:
            name = f'{self.name} — {record.display_name}'
        if not name.lower().endswith('.docx'):
            name += '.docx'
        return name
