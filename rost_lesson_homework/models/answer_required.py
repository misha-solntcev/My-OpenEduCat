# -*- coding: utf-8 -*-
# «Требуется ответ» на ДЗ: флаг на журнале урока -> op.assignment,
# подхвачивается синком rost_lesson_homework и миниаппом (обязательное
# поле «Ответ» при сдаче).
from odoo import fields, models


class OpAttendanceSheet(models.Model):
    _inherit = 'op.attendance.sheet'

    homework_answer_required = fields.Boolean('Требуется ответ при сдаче')


class OpAssignment(models.Model):
    _inherit = 'op.assignment'

    answer_required = fields.Boolean('Требуется ответ при сдаче')

    # Материалы задания (учитель прикрепляет из миниаппа).
    def _hw_store_attachments(self, files):
        """files: [{filename, mimetype, b64}] — заменить материалы."""
        self.ensure_one()
        Att = self.env['ir.attachment'].sudo()
        old = Att.search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'hw_material'),
        ])
        old.unlink()
        for f in files or []:
            Att.create({
                'name': f.get('filename') or 'attachment',
                'mimetype': f.get('mimetype') or 'application/octet-stream',
                'datas': f.get('b64') or '',
                'res_model': self._name,
                'res_id': self.id,
                'res_field': 'hw_material',
                'public': False,
            })

    def _hw_material_payload(self):
        """[{name, url}] — материалы с одноразовыми ссылками (24 ч)."""
        self.ensure_one()
        Token = self.env['hw.attachment.token']
        out = []
        atts = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'hw_material'),
        ], order='id asc')
        for att in atts:
            token = Token.sudo().create({'attachment_id': att.id})
            out.append({
                'name': att.name or 'attachment',
                'mimetype': att.mimetype or '',
                'url': '/rost_max/hw_att/%s' % token.token,
            })
        return out


class OpAssignmentSubLine(models.Model):
    _inherit = 'op.assignment.sub.line'

    # Комментарий учителя при «на доработку»/приёмке. Отдельно от note:
    # note хранит ответ ученика (миниапп пишет его при сдаче).
    teacher_note = fields.Text('Комментарий учителя')

    # Вложения сдачи (фото/файл из миниаппа). ir.attachment c res_field:
    # доступ через /web/content по id + токен не раскрывает прочие
    # вложения; выдача миниаппу — подписанные ссылки в /submissions.
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', string='Вложения сдачи',
        domain=[('res_model', '=', 'op.assignment.sub.line')])

    def _hw_store_attachments(self, files):
        """files: [{filename, mimetype, b64}] — заменить вложения сдачи."""
        self.ensure_one()
        Att = self.env['ir.attachment'].sudo()
        old = Att.search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'hw_attachment'),
        ])
        old.unlink()
        for f in files or []:
            Att.create({
                'name': f.get('filename') or 'attachment',
                'mimetype': f.get('mimetype') or 'application/octet-stream',
                'datas': f.get('b64') or '',
                'res_model': self._name,
                'res_id': self.id,
                'res_field': 'hw_attachment',
                'public': False,
            })
