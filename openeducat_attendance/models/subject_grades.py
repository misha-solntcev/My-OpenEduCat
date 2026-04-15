import re
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class OpSubjectGrades(models.Model):
    _name = "op.subject.grades"
    _description = "Subject Grades"
    _order = "student_id, subject_id"

    student_id = fields.Many2one('op.student', 'Student', required=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', compute='_compute_faculty_id', store=True)
    
    table_entries = fields.Text('Table Entries') 
    textbook_image = fields.Binary('Textbook Image', compute='_compute_textbook_image')
    student_name_short = fields.Char('Student Name Short', compute='_compute_student_name_short')
    
    # Глобальные итоги
    average_mark = fields.Float('Средняя', compute='_compute_all_data')
    total_classes = fields.Integer('Всего', compute='_compute_all_data')
    present_classes = fields.Integer('Посещено', compute='_compute_all_data')
    last_attendance_date = fields.Date('Дата последнего урока', compute='_compute_all_data')

    # Поля для вкладок (Many2many)
    q1_line_ids = fields.Many2many('op.attendance.line', compute='_compute_all_data')
    q2_line_ids = fields.Many2many('op.attendance.line', compute='_compute_all_data')
    q3_line_ids = fields.Many2many('op.attendance.line', compute='_compute_all_data')
    q4_line_ids = fields.Many2many('op.attendance.line', compute='_compute_all_data')

    # Средние баллы и счетчики по четвертям
    q1_average_mark = fields.Float(compute='_compute_all_data')
    q2_average_mark = fields.Float(compute='_compute_all_data')
    q3_average_mark = fields.Float(compute='_compute_all_data')
    q4_average_mark = fields.Float(compute='_compute_all_data')

    # Итоговые оценки (ручной ввод)
    q1_final_grade = fields.Char('Итог Q1')
    q2_final_grade = fields.Char('Итог Q2')
    q3_final_grade = fields.Char('Итог Q3')
    q4_final_grade = fields.Char('Итог Q4')
    final_quarter_grade = fields.Char('Годовая')

    # Поля аналитики для каждой четверти (счетчики оценок и отзывы)
    q1_last_remark = fields.Char(compute='_compute_all_data')
    q1_count_5 = fields.Integer(compute='_compute_all_data')
    q1_count_4 = fields.Integer(compute='_compute_all_data')
    q1_count_3 = fields.Integer(compute='_compute_all_data')
    q1_count_2 = fields.Integer(compute='_compute_all_data')

    q2_last_remark = fields.Char(compute='_compute_all_data')
    q2_count_5 = fields.Integer(compute='_compute_all_data')
    q2_count_4 = fields.Integer(compute='_compute_all_data')
    q2_count_3 = fields.Integer(compute='_compute_all_data')
    q2_count_2 = fields.Integer(compute='_compute_all_data')

    q3_last_remark = fields.Char(compute='_compute_all_data')
    q3_count_5 = fields.Integer(compute='_compute_all_data')
    q3_count_4 = fields.Integer(compute='_compute_all_data')
    q3_count_3 = fields.Integer(compute='_compute_all_data')
    q3_count_2 = fields.Integer(compute='_compute_all_data')

    q4_last_remark = fields.Char(compute='_compute_all_data')
    q4_count_5 = fields.Integer(compute='_compute_all_data')
    q4_count_4 = fields.Integer(compute='_compute_all_data')
    q4_count_3 = fields.Integer(compute='_compute_all_data')
    q4_count_2 = fields.Integer(compute='_compute_all_data')

    @api.depends('student_id', 'subject_id')
    def _compute_all_data(self):
        # 1. Оптимизация: собираем данные один раз для всех студентов на экране
        all_student_ids = self.mapped('student_id').ids
        if not all_student_ids: return

        all_lines = self.env['op.attendance.line'].search([
            ('student_id', 'in', all_student_ids)
        ], order='attendance_date desc')

        # Группируем линии в памяти по (student, subject)
        lines_map = {}
        for l in all_lines:
            s_id = l.subject_id.id or l.attendance_id.session_id.subject_id.id
            if not s_id: continue
            key = (l.student_id.id, s_id)
            if key not in lines_map: lines_map[key] = []
            lines_map[key].append(l)

        for rec in self:
            lines = lines_map.get((rec.student_id.id, rec.subject_id.id), [])
            rec.total_classes = len(lines)
            rec.present_classes = sum(1 for l in lines if l.present or l.late)
            rec.last_attendance_date = lines[0].attendance_date if lines else False

            def get_stats(l_list):
                all_m = [l.grade_1 for l in l_list if l.grade_1 > 0] + [l.grade_2 for l in l_list if l.grade_2 > 0]
                avg = round(sum(all_m) / len(all_m), 2) if all_m else 0.0
                remarks = [l.remark for l in l_list if l.remark]
                return {
                    'avg': avg, 'c5': all_m.count(5), 'c4': all_m.count(4),
                    'c3': all_m.count(3), 'c2': all_m.count(2),
                    'rem': remarks[0] if remarks else "—"
                }

            rec.average_mark = get_stats(lines)['avg']

            for q in range(1, 5):
                q_l = [l for l in lines if l.term_id and str(q) in (l.term_id.name or '')]
                stats = get_stats(q_l)
                setattr(rec, f'q{q}_line_ids', [(6, 0, [l.id for l in q_l])])
                setattr(rec, f'q{q}_average_mark', stats['avg'])
                setattr(rec, f'q{q}_count_5', stats['c5'])
                setattr(rec, f'q{q}_count_4', stats['c4'])
                setattr(rec, f'q{q}_count_3', stats['c3'])
                setattr(rec, f'q{q}_count_2', stats['c2'])
                setattr(rec, f'q{q}_last_remark', stats['rem'])

    @api.depends('subject_id', 'batch_id')
    def _compute_faculty_id(self):
        subject_ids = self.mapped('subject_id').ids
        batch_ids = self.mapped('batch_id').ids

        sessions = self.env['op.session'].search([
            ('subject_id', 'in', subject_ids),
            ('batch_id', 'in', batch_ids)
        ])

        session_map = {(s.subject_id.id, s.batch_id.id): s.faculty_id.id 
            for s in sessions}

        for record in self:
            record.faculty_id = session_map.get((record.subject_id.id, record.batch_id.id), False)
    
    
    @api.depends('student_id')
    def _compute_student_name_short(self):        
        for record in self:
            student = record.student_id
            if student:                
                name_parts = [student.first_name, student.last_name]
                record.student_name_short = " ".join(filter(None, name_parts))
            else:
                record.student_name_short = ""

    @api.depends('subject_id', 'batch_id')
    def _compute_textbook_image(self):        
        subject_ids = self.mapped('subject_id').ids        
        course_ids = self.mapped('batch_id.course_id').ids
                
        media_records = self.env['op.media'].search([
            ('subject_ids', 'in', subject_ids)
        ])

        match_map = {}
        general_map = {}

        for m in media_records:
            img = m.x_image_128
            if not img:
                continue
                
            m_subject_ids = m.subject_ids.ids
            m_course_ids = m.course_ids.ids

            for s_id in m_subject_ids:
                if s_id not in subject_ids:
                    continue
                
                if m_course_ids:                    
                    for c_id in m_course_ids:
                        if (s_id, c_id) not in match_map:
                            match_map[(s_id, c_id)] = img
                else:                    
                    if s_id not in general_map:
                        general_map[s_id] = img

        for record in self:
            s_id = record.subject_id.id
            c_id = record.batch_id.course_id.id
 
            image = match_map.get((s_id, c_id)) or general_map.get(s_id)
            
            record.textbook_image = image or False

    def action_migrate_old_data(self):
        records = self if self else self.search([])
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        total_m = 0
        for record in records.sudo():
            if not record.table_entries: continue
            student_lines = self.env['op.attendance.line'].search([('student_id', '=', record.student_id.id)])
            cache = {(str(l.attendance_date), (l.subject_id.id or l.attendance_id.session_id.subject_id.id)): l for l in student_lines}
            raw = record.table_entries.split(',')
            valid = []
            for p in raw:
                p = p.strip()
                if p.startswith('202'): valid.append(p)
                elif valid: valid[-1] += "," + p
            for entry in valid:
                parts = [p.strip() for p in entry.split('|')]
                if len(parts) < 2 or not date_pattern.match(parts[0]): continue
                line = cache.get((parts[0], record.subject_id.id))
                if not line: # fallback
                    line = next((l for k, l in cache.items() if k[0] == parts[0]), None)
                if line:
                    try:
                        vals = {}
                        if parts[1] not in ['', 'None', 'False']: vals['grade_1'] = float(parts[1].replace(',', '.'))
                        if len(parts) > 2 and parts[2] not in ['', 'None', 'False']: vals['grade_2'] = float(parts[2].replace(',', '.'))
                        if len(parts) > 7 and parts[7]: vals['remark'] = parts[7]
                        if vals: line.write(vals); total_m += 1
                    except: pass
        _logger.info("=== МИГРАЦИЯ ЗАВЕРШЕНА: %s ОЦЕНОК ===", total_m)
        return True

    def action_dump_entries_to_file(self):
        file_path = '/tmp/grades_dump.txt'
        with open(file_path, 'w', encoding='utf-8') as f:
            records = self.sudo().search([('table_entries', '!=', False)])
            for rec in records:
                f.write(f"{rec.id} | {rec.student_id.name} | {rec.subject_id.name} | {rec.table_entries}\n")
        return True