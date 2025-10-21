{
    'name': 'Unified Student Permissions',
    'version': '1.0',
    'category': 'Education',
    'summary': 'Consolidated and consistent permissions for student group',
    'description': '''
        This module provides a unified and consistent set of permissions for the student group,
        resolving contradictions and redundancies from multiple previous implementations.
        It provides appropriate access levels to contacts, employees, and other resources
        while maintaining security boundaries.
    ''',
    'author': 'Custom',
    'depends': ['base', 'hr', 'openeducat_core', 'openeducat_timetable', 'openeducat_library'],
    'data': [
        'security/student_permissions.xml',
        'views/student_permissions_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}