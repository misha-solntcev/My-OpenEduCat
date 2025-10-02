# Улучшенное Kanban-представление оценок студентов по предметам

## Общее описание
В рамках проекта было реализовано улучшенное Kanban-представление оценок студентов по предметам в системе OpenEduCat. Представление позволяет визуально отображать агрегированные данные по оценкам студентов с различными фильтрами и настройками для разных типов пользователей.

## Компоненты реализации

### 1. Модель данных (op.subject.grades)
Модель `op.subject.grades` предназначена для агрегирования данных по оценкам студентов по предметам. Она собирает информацию из записей посещаемости (`op.attendance.line`) и предоставляет удобное представление для отображения в Kanban-виде.

Подробное описание модели и ее методов: [subject_grades_model.md](subject_grades_model.md)

### 2. Wizard обновления данных (op.update.subject.grades)
Wizard `op.update.subject.grades` предназначен для обновления агрегированных данных в модели `op.subject.grades` на основе записей посещаемости из модели `op.attendance.line`.

Подробное описание wizard: [update_subject_grades_wizard.md](update_subject_grades_wizard.md)

### 3. Kanban-представление
Kanban-представление модели `op.subject.grades` предоставляет визуальное отображение оценок студентов по предметам с использованием карточек.

Подробное описание представления: [subject_grades_kanban_view.md](subject_grades_kanban_view.md)

### 4. Цветные бейджи оценок
В Kanban-представлении реализована визуализация оценок в виде цветных бейджей для лучшего восприятия информации.

Подробное описание реализации: [color_badges.md](color_badges.md)

### 5. Система прав доступа
Реализована система разграничения доступа к данным для разных типов пользователей.

Подробное описание прав доступа: [access_rights.md](access_rights.md)

## Логика фильтрации данных
Фильтрация данных реализована на уровне методов `_search` и `read` модели `op.subject.grades`. Это позволяет автоматически применять фильтрацию при любом доступе к данным.

Подробное описание логики: [filtering_logic.md](filtering_logic.md)

## Технические особенности

### Обработка строк в QWeb
Для корректной обработки строк в шаблоне QWeb используется подход:
```xml
<t t-set="final_mark" t-value="('' + mark).trim()"/>
```

### Группировка по классам
По умолчанию записи группируются по классам (`batch_id`) для удобного просмотра.

### Кнопка обновления данных
Кнопка обновления данных доступна только для пользователей с правами менеджера посещаемости и вызывает wizard `op.update.subject.grades`.

## Файлы реализации
1. Модель: `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/models/subject_grades.py`
2. Wizard обновления: `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/update_subject_grades.py`
3. Представления: `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/subject_grades_view.xml`
4. Wizard view: `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/update_subject_grades_view.xml`

## Документация
Вся документация находится в директории `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/doc/`:
- [subject_grades_model.md](subject_grades_model.md) - Модель op.subject.grades
- [update_subject_grades_wizard.md](update_subject_grades_wizard.md) - Wizard обновления данных
- [subject_grades_kanban_view.md](subject_grades_kanban_view.md) - Kanban-представление
- [color_badges.md](color_badges.md) - Цветные бейджи оценок
- [access_rights.md](access_rights.md) - Права доступа
- [filtering_logic.md](filtering_logic.md) - Логика фильтрации