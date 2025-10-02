# OpenEduCat Attendance Module Customizations Documentation

This document provides comprehensive documentation for all customizations made to the OpenEduCat attendance module in Odoo.

## 1. Enhanced Kanban View for Subject Grades

### 1.1 Overview
We've created an enhanced Kanban view that aggregates student grades by subject, providing a visual representation of all grades a student has received for each subject in a single card.

### 1.2 Features
- Aggregates all grades for each student-subject combination
- Color-coded grade badges (red for 2, yellow for 3, green for 4, blue for 5)
- Integration with textbook images from the library module
- Proper card grouping by classes
- Average grade calculation per subject
- Attendance statistics (total sessions, attended sessions)

### 1.3 Implementation Details
- New model: `op.subject.grades` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/models/subject_grades.py`
- New view: `subject_grades_view.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/subject_grades_view.xml`
- Wizard for updating aggregated data: `update_subject_grades.py` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/update_subject_grades.py`
- Wizard view: `update_subject_grades_view.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/update_subject_grades_view.xml`

### 1.4 Data Aggregation Logic
The system aggregates data from `op.attendance.line` records, grouping by student and subject to create consolidated records in the `op_subject_grades` table.

### 1.5 Access
Accessible through the menu: "Class Attendances" -> "Attendance" -> "Оценки по предметам (Kanban - Улучшенный)"

## 2. Custom Reports

### 2.1 Class Grades Summary Report

#### 2.1.1 Overview
Generates a summary report showing all grades for students in a selected class, organized by subjects with average grades calculated.

#### 2.1.2 Features
- Displays student names and all their grades organized by subject
- Shows average grade per student
- Shows class average grade
- Landscape orientation for better readability
- Russian language interface

#### 2.1.3 Implementation Details
- Report definition: `class_grades_summary_report.py` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/class_grades_summary_report.py`
- Report template: `class_grades_summary_report.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/class_grades_summary_report.xml`
- Wizard: `class_grades_summary_wizard.py` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/class_grades_summary_wizard.py`
- Wizard view: `class_grades_summary_wizard_view.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/class_grades_summary_wizard_view.xml`

#### 2.1.4 Access
Accessible through the menu: "Class Attendances" -> "Reports" -> "Сводный отчет по оценкам класса"

### 2.2 Student Grades by Date Report

#### 2.2.1 Overview
Generates a report showing student grades organized by date, allowing analysis of student performance over time for a specific subject and faculty.

#### 2.2.2 Features
- Displays student names vertically and lesson dates horizontally
- Shows grades in cells corresponding to student and date
- Includes average grade per student
- Includes class average grade
- Landscape orientation for better readability
- Filter by subject, faculty, and date range
- Default date range from academic year start to current date

#### 2.2.3 Implementation Details
- Report definition: `student_grades_by_date_report.py` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_date_report.py`
- Report template: `student_grades_by_date_report.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_date_report.xml`
- Wizard: `student_grades_by_date_wizard.py` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/student_grades_by_date_wizard.py`
- Wizard view: `student_grades_by_date_wizard_view.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/student_grades_by_date_wizard_view.xml`

#### 2.2.4 Access
Accessible through the menu: "Class Attendances" -> "Reports" -> "Отчет по оценкам студентов по датам"

### 2.3 Student Grades by Subject Report

#### 2.3.1 Overview
Generates a report showing student grades organized by subject, providing an overview of student performance across different subjects.

#### 2.3.2 Features
- Displays student names and their grades for different subjects
- Integrates with custom fields `x_mark` and `x_behavior`
- Russian language interface

#### 2.3.3 Implementation Details
- Report definition: `student_grades_by_subject_report.py` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_subject_report.py`
- Report template: `student_grades_by_subject_report.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_subject_report.xml`

#### 2.3.4 Access
Accessible through the student attendance wizard with report type selection

## 3. Custom Fields in Attendance Line Form

### 3.1 Overview
We've added custom fields to the attendance line form to capture student grades and behavior during classes.

### 3.2 Custom Fields
- `x_mark`: Field for capturing student grades (2, 3, 4, 5)
- `x_behavior`: Field for capturing student behavior notes
- `x_subject`: Field for capturing the subject of the lesson

### 3.3 Implementation Details
- View modifications: `custom_attendance_line_view.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/custom_attendance_line_view.xml`
- Field reordering for better logical flow and readability

### 3.4 Access
These fields are visible in the attendance line form when creating or editing attendance records.

## 4. Menu Structure Changes

### 4.1 Overview
We've reorganized the menu structure to improve navigation and user experience by creating a dedicated "Reports" submenu.

### 4.2 New Menu Structure
- "Class Attendances" (main menu)
  - "Attendance" (submenu)
    - "Оценки по предметам (Kanban)" - Original Kanban view for subject grades
    - "Оценки по предметам (Kanban - Улучшенный)" - Enhanced Kanban view for subject grades
  - "Reports" (new submenu)
    - "Сводный отчет по оценкам класса" - Class Grades Summary Report
    - "Отчет по оценкам студентов по датам" - Student Grades by Date Report
  - "Configuration" (existing submenu)

### 4.3 Implementation Details
- Menu modifications: `op_menu.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/menus/op_menu.xml`

## 5. User Group Permissions

### 5.1 Overview
We've added custom user groups to control access to attendance features, ensuring that both faculty and students can access the attendance sheet button.

### 5.2 Custom User Groups
- `__custom__.group_op_faculty` - Faculty user group (created through UI)
- `__custom__.group_op_students` - Student user group (created through UI)

These groups were created through the Odoo user interface and contain both faculty and student users respectively. They are used to control access to attendance features.

### 5.3 Implementation Details
- Security definitions: `op_security.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/security/op_security.xml`
- Access controls: `ir.model.access.csv` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/security/ir.model.access.csv`
- View inheritance: `custom_attendance_session_view.xml` in `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/custom_attendance_session_view.xml`

### 5.4 Access
The "Attendance Sheet" button is now visible to users in both the faculty and student groups.

## 6. Backup Procedures

### 6.1 Overview
To ensure the safety of all customizations, we've documented the key files and database tables that should be included in your regular backup procedures.

### 6.2 Key Custom Files to Backup
Your hosting provider's backup service should include these custom files:
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/models/subject_grades.py`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/subject_grades_view.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/update_subject_grades.py`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/wizards/update_subject_grades_view.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/class_grades_summary_report.py`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/class_grades_summary_report.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_date_report.py`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_date_report.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_subject_report.py`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/report/student_grades_by_subject_report.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/custom_attendance_line_view.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/custom_attendance_session_view.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/views/attendance_subject_kanban_view.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/menus/op_menu.xml`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/security/ir.model.access.csv`
- `/opt/odoo/custom-addons/openeducat_erp/openeducat_attendance/security/op_security.xml`

### 6.3 Key Database Tables to Backup
Your hosting provider's backup service should include these custom database tables:
- `op_subject_grades` - Stores aggregated grade data for the Kanban view

### 6.4 Recovery Procedures
In case of system failure, follow these steps:
1. Restore the database from your hosting provider's latest backup
2. Restore the custom files from your hosting provider's latest backup
3. Restart the Odoo service: `sudo systemctl restart odoo`
4. Update the OpenEduCat module: `sudo odoo -c /etc/odoo/odoo.conf -d rostschoolspb -u openeducat_attendance`

## 7. User Role Testing Scenarios

### 7.1 Faculty User Testing

#### 7.1.1 Test Scenario 1: Accessing Attendance Features
1. Log in as a faculty user
2. Navigate to "Class Attendances" menu
3. Verify that "Attendance Sheet" button is visible
4. Click on "Оценки по предметам (Kanban - Улучшенный)" and verify access to Kanban view
5. Navigate to "Reports" submenu and verify access to both reports

#### 7.1.2 Test Scenario 2: Generating Reports
1. Log in as a faculty user
2. Navigate to "Class Attendances" -> "Reports"
3. Generate "Сводный отчет по оценкам класса" for a class
4. Generate "Отчет по оценкам студентов по датам" with specific filters
5. Verify that reports are generated correctly with proper data

#### 7.1.3 Test Scenario 3: Updating Attendance Records
1. Log in as a faculty user
2. Navigate to an attendance session
3. Verify that custom fields `x_mark` and `x_behavior` are visible
4. Enter data in these fields and save
5. Verify that data is correctly saved in the database

### 7.2 Student User Testing

#### 7.2.1 Test Scenario 1: Accessing Attendance Features
1. Log in as a student user
2. Navigate to "Class Attendances" menu
3. Verify that "Attendance Sheet" button is visible
4. Click on "Оценки по предметам (Kanban - Улучшенный)" and verify access to Kanban view

#### 7.2.2 Test Scenario 2: Viewing Personal Grades
1. Log in as a student user
2. Navigate to "Оценки по предметам (Kanban - Улучшенный)"
3. Verify that only the student's own grades are visible
4. Verify that textbook images are displayed correctly

### 7.3 Administrator User Testing

#### 7.3.1 Test Scenario 1: Accessing All Features
1. Log in as an administrator user
2. Navigate to all attendance features
3. Verify access to all reports and views
4. Verify ability to run the "Update Subject Grades" wizard

#### 7.3.2 Test Scenario 2: Running Maintenance Wizards
1. Log in as an administrator user
2. Navigate to "Class Attendances" -> "Configuration"
3. Run the "Обновить оценки по предметам" wizard
4. Verify that the `op_subject_grades` table is updated correctly