from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from collections import defaultdict
import datetime

class GenerateSession(models.TransientModel):
    _name = "generate.time.table"
    _description = "Generate Sessions"
    _rec_name = "course_id"

    course_id = fields.Many2one('op.course', 'Класс', required=True, help="Выберите класс, для которого создается расписание")
    batch_id = fields.Many2one('op.batch', 'Параллель', required=True, help="Выберите параллель")    
    
    start_date = fields.Date('Дата начала генерации', required=True, default=fields.Date.context_today, help="Дата, с которой начнутся занятия")
    end_date = fields.Date('Дата окончания генерации', required=True, 
        default=lambda self: (fields.Date.context_today(self) + datetime.timedelta(days=30)).replace(day=1) - datetime.timedelta(days=1))
    
    import_start_date = fields.Date('Начало периода импорта', help="Начало периода, из которого копируем уроки")
    import_end_date = fields.Date('Конец периода импорта', help="Конец периода, из которого копируем уроки")

    time_table_lines = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines')
    time_table_lines_1 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '0')])
    time_table_lines_2 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '1')])
    time_table_lines_3 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '2')])
    time_table_lines_4 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '3')])
    time_table_lines_5 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '4')])
    time_table_lines_6 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '5')])
    time_table_lines_7 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '6')])
    
    show_stats = fields.Boolean('Показать статистику', default=False)    
    subject_stats_info = fields.Html('Статистика нагрузки', compute='_compute_all_stats')
    faculty_stats_info = fields.Html('Нагрузка учителей', compute='_compute_all_stats')

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:            
            next_month = self.start_date.replace(day=28) + datetime.timedelta(days=4)
            self.end_date = next_month.replace(day=1) - datetime.timedelta(days=1)

    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id:
            batches = self.env['op.batch'].search([('course_id', '=', self.course_id.id)])
            self.batch_id = batches[0].id if len(batches) == 1 else False
        
    @api.onchange('batch_id')
    def _onchange_batch_id(self):
        """Автозаполнение кабинета во всех строках при выборе группы"""
        if self.batch_id:
            classroom = self.env['op.classroom'].search([('batch_id', '=', self.batch_id.id)], limit=1)
            if classroom:                
                for f_name, f_obj in self._fields.items():
                    if f_obj.type == 'one2many' and f_obj.comodel_name == 'gen.time.table.line':
                        lines = self[f_name]
                        if lines:
                            lines.write({'classroom_id': classroom.id})

    # --- ГЛАВНЫЙ ДВИЖОК ГЕНЕРАЦИИ (REFUCTORED) ---
    def act_gen_time_table(self):
        self.ensure_one()
        if not self.time_table_lines:
            raise ValidationError(_("Таблица расписания не заполнена."))

        # 1. Проверка на дубликаты
        existing = self.env['op.session'].search_count([
            ('batch_id', '=', self.batch_id.id),
            ('timetable_date', '>=', self.start_date),
            ('timetable_date', '<=', self.end_date),
            ('state', '!=', 'cancel'),
        ])
        if existing > 0:
            raise ValidationError(_("Для этого класса уже создано %s уроков. Сначала удалите их.") % existing)

        sessions_data = []
        curr_date = self.start_date
        while curr_date <= self.end_date:
            weekday = str(curr_date.weekday())
            day_lines = self.time_table_lines.filtered(lambda l: l.day == weekday)
            
            for line in day_lines:
                # ВАЖНО: Используем метод Mixin для получения точного UTC
                # Он учтет, что сетка звонков Московская, а база Odoo ждет UTC.
                sync = self._sync_time_values(date_val=curr_date, timing_id=line.timing_id.id)
                
                if sync:
                    sessions_data.append({
                        'course_id': self.course_id.id,
                        'batch_id': self.batch_id.id,
                        'faculty_id': line.faculty_id.id,
                        'subject_id': line.subject_id.id,
                        'classroom_id': line.classroom_id.id,
                        'timing_id': line.timing_id.id,
                        'start_datetime': sync['start_datetime'],
                        'end_datetime': sync['end_datetime'],
                        'timetable_date': sync['timetable_date'],
                    })
            curr_date += datetime.timedelta(days=1)

        if sessions_data:
            self.env['op.session'].create(sessions_data)
        return {'type': 'ir.actions.act_window_close'}

    # --- СТАТИСТИКА ---
    @api.depends('show_stats', 'time_table_lines_1', 'time_table_lines_2', 'time_table_lines_3', 
                 'time_table_lines_4', 'time_table_lines_5', 'time_table_lines_6', 'time_table_lines_7')
    def _compute_all_stats(self):
        for rec in self:
            if not rec.show_stats:
                rec.subject_stats_info = rec.faculty_stats_info = False
                continue
            
            # lines = (rec.time_table_lines_1 | rec.time_table_lines_2 | rec.time_table_lines_3 | 
            #          rec.time_table_lines_4 | rec.time_table_lines_5 | rec.time_table_lines_6 | rec.time_table_lines_7)
            
            lines = rec.time_table_lines

            subj_data = defaultdict(int)
            fac_data = defaultdict(int)
            for l in lines:
                if l.subject_id: subj_data[l.subject_id] += 1
                if l.faculty_id: fac_data[l.faculty_id.name] += 1

            # Рендерим HTML для предметов
            s_res = ['<div class="d-flex flex-wrap gap-2 ps-2" style="font-size: 15px;"><b>📚 Предметы:</b>']
            for subj, count in sorted(subj_data.items(), key=lambda x: x[0].sequence):
                s_res.append(f'<span class="badge rounded-pill o_tag o_tag_subtle o_tag_color_{subj.color} border px-2 py-1">{subj.name}: {count}</span>')
            rec.subject_stats_info = "".join(s_res) + "</div>"

            # Рендерим HTML для учителей
            f_res = ['<div class="d-flex flex-wrap gap-2 ps-2 mt-2" style="font-size: 15px;"><b>👨‍🏫 Учителя:</b>']
            for name, count in sorted(fac_data.items()):
                bg = "background: #dc3545; color: white;" if count > 30 else "background: #f8f9fa; border: 1px solid #ddd;"
                f_res.append(f'<span class="badge rounded-pill px-2 py-1" style="{bg}">{name}: {count}</span>')
            rec.faculty_stats_info = "".join(f_res) + "</div>"

    def action_toggle_stats(self):
        """Ручное переключение видимости статистики"""
        self.show_stats = not self.show_stats
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('time_table_lines_1', 'time_table_lines_2', 'time_table_lines_3', 
                  'time_table_lines_4', 'time_table_lines_5', 'time_table_lines_6', 'time_table_lines_7')
    def _onchange_refresh_stats(self):
        """Принудительный пересчет HTML-статистики при изменении строк"""
        self._compute_all_stats()

    def action_clear_all(self):
        # self.ensure_one()        
        self.time_table_lines.unlink()        
        return self._reopen_wizard()    

    def action_clear_day(self):        
        # self.ensure_one()
        day = self.env.context.get('day_to_clear')
        if day is not None:
            self.time_table_lines.filtered(lambda l: l.day == str(day)).unlink()
        return self._reopen_wizard()

    def _reopen_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }       

    def action_import_last_week(self):
        self.ensure_one()
        if not (self.import_start_date and self.import_end_date):
            raise ValidationError(_("Выберите даты для импорта."))

        sessions = self.env['op.session'].search([
            ('batch_id', '=', self.batch_id.id),
            ('timetable_date', '>=', self.import_start_date),
            ('timetable_date', '<=', self.import_end_date),
            ('state', '!=', 'cancel'),
            ('timing_id', '!=', False),
        ], order='timetable_date desc')

        if not sessions:
            raise ValidationError(_("Уроков для импорта не найдено."))

        # Собираем уникальные слоты по дням недели
        seen = set()
        lines_data = []
        for s in sessions:
            day = str(s.timetable_date.weekday())
            if (day, s.timing_id.id) in seen: continue
            seen.add((day, s.timing_id.id))
            lines_data.append((0, 0, {
                'day': day, 'timing_id': s.timing_id.id, 'faculty_id': s.faculty_id.id,
                'subject_id': s.subject_id.id, 'classroom_id': s.classroom_id.id,
            }))

        self.time_table_lines.unlink() # Очищаем перед импортом
        self.write({'time_table_lines': lines_data})
        return self._reopen_wizard()

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("Дата окончания периода не может быть раньше даты начала."))


class GenerateSessionLine(models.TransientModel):
    _name = 'gen.time.table.line'
    _description = 'Generate Time Table Lines'
    _rec_name = 'timing_id'

    gen_time_table = fields.Many2one('generate.time.table', 'Time Table', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Учитель', required=True)
    subject_id = fields.Many2one('op.subject', 'Предмет', required=True,
        domain="[('id', 'in', faculty_subject_ids)]")
    faculty_subject_ids = fields.Many2many('op.subject', related='faculty_id.faculty_subject_ids')
    timing_id = fields.Many2one('op.timing', 'Урок', required=True)
    classroom_id = fields.Many2one('op.classroom', 'Кабинет')
    day = fields.Selection([
        ('0', 'Понедельник'),
        ('1', 'Вторник'),
        ('2', 'Среда'),
        ('3', 'Четверг'),
        ('4', 'Пятница'),
        ('5', 'Суббота'),
        ('6', 'Воскресенье'),
    ], 'День', required=True)

    @api.onchange('faculty_id')
    def _onchange_faculty_id(self):
        # 1. Подставляем кабинет при выборе учителя, если он еще не выбран
        if self.gen_time_table.batch_id and not self.classroom_id:
            classroom = self.env['op.classroom'].search([('batch_id', '=', self.gen_time_table.batch_id.id)], limit=1)
            if classroom:
                self.classroom_id = classroom.id
        
        # 2. Автоматически подставляем предмет, если у учителя он только один
        if self.faculty_id and self.faculty_id.faculty_subject_ids:
            if len(self.faculty_id.faculty_subject_ids) == 1:
                self.subject_id = self.faculty_id.faculty_subject_ids[0].id

    @api.onchange('timing_id')
    def _onchange_timing_id_filter(self):
        """Возвращает динамический фильтр для выпадающего списка уроков"""
        if self.day:
            day_field = 'time_table_lines_%s' % (int(self.day) + 1)
            used_timing_ids = self.gen_time_table[day_field].mapped('timing_id').ids
            current_id = self.timing_id.id or (self._origin.timing_id.id if hasattr(self, '_origin') else False)
            other_used_ids = [tid for tid in used_timing_ids if tid != current_id]
            return {'domain': {'timing_id': [('id', 'not in', other_used_ids)]}}

    @api.onchange('gen_time_table.batch_id')
    def _onchange_classroom_id(self):
        for rec in self:
            if rec.gen_time_table.batch_id:
                classroom = self.env['op.classroom'].search([
                    ('batch_id', '=', rec.gen_time_table.batch_id.id)
                ], limit=1)
                if classroom:
                    rec.classroom_id = classroom.id


    