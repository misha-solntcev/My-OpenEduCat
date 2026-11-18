# -*- coding: utf-8 -*-
"""Вложения школы: удаление сгенерированных документов.

ACL ядра даёт внутреннему пользователю полный доступ к ir.attachment
(включая unlink), поэтому право на удаление документов школы срезается
на методе кнопки: корзина доступна только Администратору.
"""
from odoo import _, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def rost_unlink_document(self):
        """Удалить сгенерированный документ (корзина во вкладке «Договор»).

        Клик по строке файла в списке doc_file_ids. Метод вешается на
        ir.attachment, чтобы кнопка жила прямо в строке вложения.
        """
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_(
                'Удалять сгенерированные документы может только Администратор.'))
        self.unlink()
        # reload: список файлов — несторовый compute на форме договора,
        # без перезагрузки удалённая строка остаётся висеть до F5.
        return {'type': 'ir.actions.client', 'tag': 'reload'}
