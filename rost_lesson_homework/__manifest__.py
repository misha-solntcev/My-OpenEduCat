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
        'mail',
    ],
    'data': [
        'views/attendance_sheet_homework_view.xml',
        'views/attendance_hw_grades.xml',
        # ПК-форма сдачи: комментарий учителя, вложения, русские кнопки.
        # После attendance_hw_grades — модель op.assignment.sub.line уже
        # расширена в models/answer_required.py к моменту загрузки view.
        'views/assignment_sub_line_hw_view.xml',
        'views/assignment_sub_line_works_view.xml',
        # ПК-форма задания: выдача с объявлением и счётом срока, русские
        # кнопки состояния, вкладка «Работы», ссылка на урок.
        'views/assignment_hw_view.xml',
    ],
    'assets': {
        # Виджет кружков оценки (marks/marks_2), тап как в миниаппе.
        'web.assets_backend': [
            'rost_lesson_homework/static/src/hw_marks_field.js',
            'rost_lesson_homework/static/src/hw_marks_field.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
