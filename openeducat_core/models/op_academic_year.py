from datetime import timedelta
from odoo import fields, models, api, _

class OpAcademicYear(models.Model):
    _name = 'op.academic.year'
    _description = "Academic Year"

    name = fields.Char('Name', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    create_boolean = fields.Boolean('Terms Created', default=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    term_structure = fields.Selection([
        ('two_sem', 'Two Semesters'),
        ('two_sem_qua', 'Two Semesters divided by Quarters'),
        ('three_sem', 'Three Trimesters'),
        ('four_Quarter', 'Four Quarters'),
        ('final_year', 'Full Year divided by Quarters'),
        ('others', 'Other (Manual)')
    ], string='Term Structure', default='two_sem', required=True)

    academic_term_ids = fields.One2many('op.academic.term', 'academic_year_id', string='Academic Terms')

    def _get_split_dates(self, start, end, parts):
        """Вспомогательный метод: делит период на N равных частей"""
        delta = (end - start).days + 1
        avg_days = delta // parts
        res = []
        curr_start = start
        for i in range(parts):
            # Последняя часть забирает остаток дней (чтобы не терять секунды/дни)
            if i == parts - 1:
                curr_end = end
            else:
                curr_end = curr_start + timedelta(days=avg_days - 1)
            res.append((curr_start, curr_end))
            curr_start = curr_end + timedelta(days=1)
        return res

    def term_create(self):
        self.ensure_one()
        if self.create_boolean or self.term_structure == 'others':
            return False

        term_obj = self.env['op.academic.term']
        
        # Конфигурация структур: (Кол-во семестров, Кол-во под-периодов в каждом)
        structures = {
            'two_sem': (2, 0),
            'three_sem': (3, 0),
            'four_Quarter': (4, 0),
            'two_sem_qua': (2, 2),  # 2 семестра по 2 четверти
            'final_year': (1, 4),   # 1 год по 4 четверти
        }

        sem_count, sub_count = structures.get(self.term_structure, (0, 0))
        if not sem_count:
            return False

        # 1. Генерируем основные периоды (Семестры)
        sem_dates = self._get_split_dates(self.start_date, self.end_date, sem_count)
        
        quarter_idx = 1
        for idx, (s_date, e_date) in enumerate(sem_dates, 1):
            sem_name = f"Semester {idx}" if self.term_structure != 'final_year' else "Full Year"
            parent_term = term_obj.create({
                'name': sem_name,
                'term_start_date': s_date,
                'term_end_date': e_date,
                'academic_year_id': self.id,
            })

            # 2. Если нужно, делим семестры на под-периоды (Четверти)
            if sub_count > 0:
                sub_dates = self._get_split_dates(s_date, e_date, sub_count)
                for (sub_s, sub_e) in sub_dates:
                    term_obj.create({
                        'name': f"Quarter {quarter_idx}",
                        'term_start_date': sub_s,
                        'term_end_date': sub_e,
                        'academic_year_id': self.id,
                        'parent_term': parent_term.id,
                    })
                    quarter_idx += 1

        self.create_boolean = True
        return True