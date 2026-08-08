"""Post-migration script: No state migration needed - both pass_out and left are valid final states"""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """No migration needed - both pass_out and left are valid states.
    Existing pass_out records remain as pass_out (graduated 11th grade).
    left is for students who left before 11th grade.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Just log current state distribution
    states = env['op.student'].read_group([], ['state'], ['state'])
    for s in states:
        print(f"State {s['state']}: {s['state_count']} students")
    
    print("Migration completed - no state changes made")