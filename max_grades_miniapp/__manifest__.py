{
    "name": "MAX Grades Mini App",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "ЧОУ СПБГШ 'РОСТ'",
    "website": "https://rostschoolspb.ru",
    "summary": "Mini app for entering grades via MAX messenger",
    "description": """
        Web interface for teachers to enter student grades.
        Designed to work as a MAX messenger mini app.
    """,
    "depends": ["base", "web", "openeducat_core", "openeducat_attendance"],
    "data": [
        "views/templates/grades_templates.xml",
    ],
    "installable": True,
    "application": False,
}