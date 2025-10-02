# OpenEduCat Attendance Module

This module extends the standard OpenEduCat attendance functionality with custom features for improved user experience and reporting.

## Key Customizations

### Enhanced Kanban View for Subject Grades
- Visual representation of student grades aggregated by subject
- Color-coded grade badges for quick assessment
- Integration with textbook images from the library module
- Proper card grouping by classes
- Access control for different user groups (faculty and students)

### Custom Reports
1. **Class Grades Summary Report**
   - Summary of all grades for students in a selected class
   - Organized by subjects with average grades calculated
   - Landscape orientation for better readability

2. **Student Grades by Date Report**
   - Analysis of student performance over time
   - Filter by subject, faculty, and date range
   - Default date range from academic year start to current date

3. **Student Grades by Subject Report**
   - Overview of student performance across different subjects
   - Integration with custom fields `x_mark` and `x_behavior`

### Custom Fields
- `x_mark`: Field for capturing student grades (2, 3, 4, 5)
- `x_behavior`: Field for capturing student behavior notes
- `x_subject`: Field for capturing the subject of the lesson

### Menu Structure
- Reorganized menu with dedicated "Reports" submenu
- Improved navigation and user experience
- Separate menu items for original and enhanced Kanban views

### User Group Permissions
- Using custom user groups created through UI:
  - `__custom__.group_op_faculty` for faculty users
  - `__custom__.group_op_students` for student users
- Controlled access to attendance features
- Proper data filtering for student users (students can only see their own grades)

## Documentation
For detailed documentation of all customizations, see [DOCUMENTATION.md](DOCUMENTATION.md)

## Backup Procedures
As you're using your hosting provider's backup service, we've documented the key files and database tables that should be included in your regular backups. See [DOCUMENTATION.md](DOCUMENTATION.md#6-backup-procedures) for details.

## Testing
Test scenarios for different user roles are documented in [DOCUMENTATION.md](DOCUMENTATION.md#7-user-role-testing-scenarios).