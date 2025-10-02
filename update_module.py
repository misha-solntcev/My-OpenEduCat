#!/usr/bin/env python3
import sys
import os

# Добавляем пути к Odoo
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo.modules.registry import Registry
from odoo.api import Environment
from odoo.tools import config

# Загружаем конфигурацию
config.parse_config(['-c', '/etc/odoo/odoo.conf'])

# Подключаемся к базе данных
db_name = 'odoo'  # Замените на имя вашей базы данных, если оно другое
registry = Registry(db_name)
with registry.cursor() as cr:
    env = Environment(cr, odoo.SUPERUSER_ID, {})
    # Ищем модуль
    module = env['ir.module.module'].search([('name', '=', 'openeducat_timetable')])
    if module:
        print(f"Updating module openeducat_timetable...")
        # Обновляем модуль
        module.button_immediate_upgrade()
        print(f"Module openeducat_timetable updated successfully.")
    else:
        print(f"Module openeducat_timetable not found.")