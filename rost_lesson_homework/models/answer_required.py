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

    # Материалы задания (учитель прикрепляет из миниаппа или ПК-формы).
    # Хранение — Many2many rel-таблица (см. material_ids выше), тот же
    # набор, что видит many2many_binary на ПК.
    def _hw_store_attachments(self, files, replace=True):
        """files: [{filename, mimetype, b64}] — материалы задания.

        replace=True  — заменить набор целиком (как было раньше).
        replace=False — ДОБАВИТЬ к текущему набору (append).

        Зачем append: фронт шлёт только НОВЫЕ файлы (у него нет доступа к
        байтам уже загруженных), поэтому полная замена при каждом
        прикреплении затирала предыдущие файлы — прикрепил второй, первый
        исчез. С фронта прикрепление всегда идёт как append; replace
        оставлен для скриптов/миграций, которым нужен точный набор.
        """
        self.ensure_one()
        Att = self.env['ir.attachment'].sudo()
        old = self.material_ids
        new_ids = [] if replace else old.ids
        for f in files or []:
            att = Att.create({
                'name': f.get('filename') or 'attachment',
                'mimetype': f.get('mimetype') or 'application/octet-stream',
                'datas': f.get('b64') or '',
                'res_model': self._name,
                'res_id': self.id,
                'public': False,
            })
            new_ids.append(att.id)
        self.sudo().material_ids = [(6, 0, new_ids)]
        # Осиротевшие вложения предыдущего набора удаляем физически.
        # При append старые входят в new_ids, поэтому удаляются только
        # действительно исчезнувшие из набора.
        old.exists().filtered(lambda a: a.id not in new_ids).sudo().unlink()

    def _hw_material_payload(self):
        """[{id, name, mimetype, url}] — материалы с одноразовыми ссылками (24 ч).

        id вложения нужен фронту для удаления ошибочно загруженного файла
        (см. api_homework_materials_delete). Раньше его не было, и удалить
        конкретный файл было нечем — только заменить весь набор.
        """
        self.ensure_one()
        Token = self.env['hw.attachment.token']
        out = []
        for att in self.material_ids.sorted('id'):
            token = Token.sudo().create({'attachment_id': att.id})
            out.append({
                'id': att.id,
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
