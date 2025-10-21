{
    'name': 'Custom Attendance Extension',
    'version': '1.0',
    'category': 'Education',
    'summary': 'Расширение функциональности модуля посещаемости',
    'description': """
Расширение функциональности модуля посещаемости OpenEduCat
=========================================================

Этот модуль добавляет поле "Тема урока" в ведомость посещаемости и передает его в оценки по предметам.
""",
    'depends': ['openeducat_attendance'],
    'data': [
        'views/attendance_sheet_view.xml',
        'views/subject_grades_view.xml',
        'views/session_planning_view.xml',
        'views/lesson_themes_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}