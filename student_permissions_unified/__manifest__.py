{
    'name': 'Unified Student and Faculty Permissions',
    'version': '1.0',
    'category': 'Education',
    'license': 'LGPL-3',
    'depends': [
        'base', 'openeducat_core', 'openeducat_attendance', 
        'openeducat_assignment', 'openeducat_exam', 'openeducat_library',
        'openeducat_timetable', 'openeducat_fees', 'openeducat_admission'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/student_permissions.xml',
    ],
    'installable': True,
    'application': False,
}
