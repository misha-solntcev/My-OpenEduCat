"""Post-migration script: Sync student states based on course details and mark 11th grade as graduating"""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Sync student states and mark graduating course"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Mark 11th grade course as graduating
    course_11 = env['op.course'].search([('name', 'ilike', '11%класс')], limit=1)
    if not course_11:
        course_11 = env['op.course'].search([('id', '=', 27)], limit=1)
    
    if course_11:
        course_11.write({'is_graduating': True})
        print(f"✓ Marked course '{course_11.name}' (ID: {course_11.id}) as graduating")
    else:
        print("⚠ Course 11th grade not found")
    
    # 2. Sync student states based on course details
    students = env['op.student'].search([])
    
    stats = {'studying': 0, 'pass_out': 0, 'left': 0, 'draft': 0, 'admission': 0, 'unchanged': 0}
    
    for student in students:
        old_state = student.state
        
        running_courses = student.course_detail_ids.filtered(lambda c: c.state == 'running')
        finished_courses = student.course_detail_ids.filtered(lambda c: c.state == 'finished')
        
        # Determine new state
        if running_courses:
            # Has active course -> studying
            new_state = 'studying'
        elif finished_courses:
            # No active courses, has finished ones
            # Check if any finished course is graduating
            has_graduating = any(c.course_id.is_graduating for c in finished_courses)
            if has_graduating:
                new_state = 'pass_out'
            else:
                new_state = 'left'
        else:
            # No courses at all - keep current state if it's draft/admission, else draft
            if student.state in ['draft', 'admission']:
                new_state = student.state
            else:
                new_state = 'draft'
        
        if new_state != old_state:
            student.write({'state': new_state})
            stats[new_state] += 1
            print(f"  Student {student.id} ({student.name}): {old_state} → {new_state}")
        else:
            stats['unchanged'] += 1
    
    print(f"\n=== Migration Summary ===")
    print(f"  studying:   {stats['studying']}")
    print(f"  pass_out:   {stats['pass_out']}")
    print(f"  left:       {stats['left']}")
    print(f"  draft:      {stats['draft']}")
    print(f"  admission:  {stats['admission']}")
    print(f"  unchanged:  {stats['unchanged']}")
    print(f"  Total:      {sum(stats.values())}")