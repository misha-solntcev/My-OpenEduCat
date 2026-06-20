{
    "name": "MAX Messenger Gateway",
    "summary": """
        Gateway integration for MAX messenger (platform-api.max.ru)""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "ЧОУ СПБГШ 'РОСТ'",
    "website": "https://rostschool.ru",
    "depends": ["mail_gateway", "mail_gateway_telegram_standalone"],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_gateway_views.xml",
    ],
    "external_dependencies": {"python": ["requests"]},
    "assets": {
        "mail.assets_messaging": [
            "mail_gateway_max/static/src/models/**/*.js",
            "mail_gateway_max/static/src/components/**/*.xml",
        ],
    },
    "installable": True,
    "application": False,
}
