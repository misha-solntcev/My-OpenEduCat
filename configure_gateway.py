import os, sys
os.environ["ODOO_RC"] = "/etc/odoo/odoo.conf"
sys.argv = ["odoo", "--db_host", "db", "-d", "test4", "--stop-after-init", "--no-xmlrpc"]

import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config

config.parse_config(sys.argv[1:])

dbname = "test4"
registry = odoo.modules.registry.Registry(dbname)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    tunnel_url = "https://ce9bc30f8cf825.lhr.life"
    ICP = env["ir.config_parameter"]
    ICP.set_param("web.base.url", tunnel_url)
    print("OK:", ICP.get_param("web.base.url"))

    import secrets
    webhook_key = secrets.token_hex(16)
    webhook_secret = secrets.token_hex(32)

    admin = env.ref("base.user_admin")
    gateway = env["mail.gateway"].create({
        "name": "Telegram Bot test4",
        "token": "8620969068:***",
        "gateway_type": "telegram",
        "webhook_key": webhook_key,
        "webhook_secret": webhook_secret,
        "webhook_user_id": admin.id,
        "integrated_webhook_state": "pending",
    })
    print("OK: id=%d" % gateway.id)
    print("OK: key=%s" % webhook_key)
    print("OK: secret=%s" % webhook_secret)
    print("OK: url=%s" % gateway.webhook_url)

    cr.commit()
    print("OK: committed")

print("DONE")
