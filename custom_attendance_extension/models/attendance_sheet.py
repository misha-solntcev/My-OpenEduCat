# -*- coding: utf-8 -*-
###############################################################################
#
#    Custom Attendance Extension - OpenEduCat
#    Copyright (C) 2025
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

from odoo import models, fields


class OpAttendanceSheet(models.Model):
    """Модель ведомости посещаемости с дополнительным полем темы урока"""
    _inherit = "op.attendance.sheet"

    # Добавляем поле для темы урока
    lesson_topic = fields.Char(
        'Тема урока', 
        size=256,
        help="Тема урока, которая будет отображаться в оценках по предметам"
    )