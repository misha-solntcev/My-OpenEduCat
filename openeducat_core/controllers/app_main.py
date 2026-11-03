###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import werkzeug.utils
from odoo import http
from odoo.addons.portal.controllers.web import Home as home
from odoo.addons.web.controllers.utils import is_user_internal
from odoo.http import request


class OpeneducatHome(home):

    @http.route()
    def web_login(self, redirect=None, *args, **kw):
        response = super(OpeneducatHome, self).web_login(
            redirect=redirect, *args, **kw)
        # При включённой 2FA сессия не авторизуется сразу: Odoo кладёт uid в
        # session.pre_uid, а request.uid остаётся пустым, и super() уже вернул
        # редирект на страницу ввода кода (/web/login/totp). Обращаться к
        # browse(request.uid) в этот момент нельзя — пустой recordset.
        if not redirect and request.params['login_success'] and request.uid:
            if request.env['res.users'].browse(request.uid).has_group(
                    'base.group_user'):
                redirect = '/web?' + request.httprequest.query_string.decode('utf-8')
            else:
                if request.env.user.is_parent:
                    redirect = '/my/child'
                else:
                    redirect = '/my'
            return werkzeug.utils.redirect(redirect)
        return response

    def _login_redirect(self, uid, redirect=None):
        # внутренние пользователи — штатный путь ядра (бэкенд), портал — в кабинет;
        # иначе после ввода кода 2FA сотрудник попадает на /my вместо бэкенда
        if redirect or is_user_internal(uid):
            return super(OpeneducatHome, self)._login_redirect(uid, redirect)
        if request.env.user.is_parent:
            return '/my/child'
        return '/my'
