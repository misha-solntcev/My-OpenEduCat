# -*- coding: utf-8 -*-
"""Мастер генерации документа: выбор шаблона реестра -> .docx -> вложение
на записи -> скачивание."""
import base64
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MIMETYPE_DOCX = ('application/vnd.openxmlformats-officedocument'
                 '.wordprocessingml.document')


class RostDocGenerateWizard(models.TransientModel):
    _name = 'rost.doc.generate.wizard'
    _description = 'Генерация документа школы'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    template_id = fields.Many2one(
        'rost.doc.template', 'Шаблон документа', required=True,
        domain="[('res_model', '=', res_model), ('active', '=', True)]")
    target_display = fields.Char(
        'Документ для', compute='_compute_target_display')

    @api.depends('res_model', 'res_id')
    def _compute_target_display(self):
        for rec in self:
            model = rec.res_model and self.env.get(rec.res_model)
            rec.target_display = (model.browse(rec.res_id).display_name
                                  if model and rec.res_id else '')

    def action_generate(self):
        self.ensure_one()
        rec = self.env[self.res_model].browse(self.res_id).exists()
        if not rec:
            raise UserError(_('Запись-источник удалена.'))
        template = self.template_id.sudo()
        if not template.template_file:
            raise UserError(_(
                'У шаблона «%s» не загружен файл .docx.') % template.name)
        context = rec._rost_doc_context()

        # Номер и дата договора: пустые -> номер из последовательности,
        # дата = сегодня. Вписанные вручную не трогаем.
        if isinstance(rec.id, int) and hasattr(rec, 'doc_number'):
            vals = {}
            if not rec.doc_number:
                vals['doc_number'] = self.env['ir.sequence'].next_by_code(
                    'rost_school_billing.doc_number')
            if not rec.doc_date:
                vals['doc_date'] = fields.Date.context_today(self)
            if vals:
                rec.write(vals)
                context = rec._rost_doc_context()

        try:
            data = base64.b64decode(template.template_file)
            from ..models.doc_engine import render_docx
            docx_bytes = render_docx(data, context)
        except UserError:
            raise
        except Exception as exc:
            raise UserError(_(
                'Не удалось заполнить шаблон «%s»: %s\n\n'
                'Проверьте токены шаблона и данные записи (пустые поля '
                'карточек дают пустые значения в документе).')
                % (template.name, exc))

        filename = template._rost_filename(rec, context)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(docx_bytes),
            'mimetype': MIMETYPE_DOCX,
            'res_model': rec._name,
            'res_id': rec.id,
        })
        if hasattr(rec, 'message_post'):
            try:
                rec.message_post(
                    body=_('Сгенерирован документ: %s') % filename,
                    attachment_ids=[attachment.id])
            except Exception:
                pass
        return {
            'type': 'ir.actions.act_url',
            'url': ('/web/content/ir.attachment/%s/datas?download=true'
                    '&filename=%s') % (attachment.id, quote(filename)),
            'target': 'self',
        }
