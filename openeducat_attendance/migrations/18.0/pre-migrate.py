def migrate(cr, version):
    cr.execute("""
        ALTER TABLE op_subject_grades 
        ADD COLUMN IF NOT EXISTS table_entries TEXT
    """)

