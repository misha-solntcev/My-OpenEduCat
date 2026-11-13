# -*- coding: utf-8 -*-
"""Регрессия на /web/image для op.parent.

У op.parent поле ``name`` — many2one, и база по умолчанию берёт из него
имя файла для потока, падая на recordset.replace() → 500 на любом
/web/image/op.parent/<id>/<field>. Фикс — ir_binary в этом модуле;
тест закрепляет поведение, чтобы «убрать костыль» можно было только
сознательно.
"""
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestParentImageStream(HttpCase):

    def test_parent_image_stream_is_200(self):
        parent = self.env['op.parent'].search([], limit=1)
        if not parent:
            self.skipTest('в базе нет ни одного родителя')

        user = self.env['res.users'].with_context(
            no_reset_password=True).create({
                'name': 'Image Stream Test',
                'login': 't_image_stream_rost',
                'password': 't_image_stream_rost',
                'groups_id': [(6, 0, [
                    self.env.ref('base.group_user').id,
                    self.env.ref('openeducat_parent.group_op_parent_manager').id,
                ])],
            })
        self.authenticate(user.login, 't_image_stream_rost')

        for field in ('avatar_128', 'image_1920'):
            response = self.url_open(
                '/web/image/op.parent/%d/%s' % (parent.id, field))
            self.assertEqual(
                response.status_code, 200,
                '/web/image/op.parent/%d/%s вернул %s (ожидался 200)'
                % (parent.id, field, response.status_code))
