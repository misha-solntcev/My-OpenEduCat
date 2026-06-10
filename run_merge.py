#!/usr/bin/env python3
"""Запуск merge_duplicates.py через Odoo shell."""
import odoo
from odoo.tools import config

config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'test4'])

with odoo.service.server.start(preload=['test4']) as env:
    exec(open('/mnt/extra-addons/merge_duplicates.py').read())
