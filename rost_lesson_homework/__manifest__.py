{
    'name': 'Rost Lesson Homework',
    'version': '18.0.1.0',
    'license': 'LGPL-3',
    'category': 'Education',
    'summary': 'Домашнее задание в журнале урока -> op.assignment',
    'author': 'Rost School',
    'depends': [
        'openeducat_attendance',
        'openeducat_assignment',
    ],
    'data': [
        'views/attendance_sheet_homework_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
