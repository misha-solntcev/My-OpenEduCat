import datetime
import pytz
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class GenerateSession(models.TransientModel):
    _name = "generate.time.table"
    _description = "Generate Sessions"
    _rec_name = "course_id"

    course_id = fields.Many2one('op.course', 'Course', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    time_table_lines = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines')
    time_table_lines_1 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '0')])
    time_table_lines_2 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '1')])
    time_table_lines_3 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '2')])
    time_table_lines_4 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '3')])
    time_table_lines_5 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '4')])
    time_table_lines_6 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '5')])
    time_table_lines_7 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '6')])
    start_date = fields.Date('С', required=True, default=fields.Date.context_today)
    end_date = fields.Date('По', required=True, 
        default=lambda self: (fields.Date.context_today(self) + datetime.timedelta(days=30)).replace(day=1) - datetime.timedelta(days=1))
    import_week_date = fields.Date('Копировать неделю от...', help="Выберите любую дату недели, структуру которой хотите взять за основу")

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:
            # По умолчанию ставим конец месяца от даты начала
            next_month = self.start_date.replace(day=28) + datetime.timedelta(days=4)
            self.end_date = next_month.replace(day=1) - datetime.timedelta(days=1)

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("Дата окончания периода не может быть раньше даты начала."))

    @api.onchange('batch_id')
    def _onchange_batch_id_update_lines(self):
        if self.batch_id:
            classroom = self.env['op.classroom'].search([('batch_id', '=', self.batch_id.id)], limit=1)
            if classroom:
                # Универсальный обход всех One2many полей, связанных со строками расписания
                # Это гарантирует работу даже при добавлении 8-го, 9-го и т.д. уроков
                for f_name, f_obj in self._fields.items():
                    if f_obj.type == 'one2many' and f_obj.comodel_name == 'gen.time.table.line':
                        lines = self[f_name]
                        if lines:
                            lines.write({'classroom_id': classroom.id})

    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id:
            batches = self.env['op.batch'].search([('course_id', '=', self.course_id.id)])
            self.batch_id = batches[0].id if len(batches) == 1 else False
        else:
            self.batch_id = False

    def change_tz(self, date):
        local_tz = pytz.timezone(
            self.env.user.partner_id.tz or 'GMT')
        local_dt = local_tz.localize(date, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        return datetime.datetime.strptime(
            utc_dt, "%Y-%m-%d %H:%M:%S")

    def act_gen_time_table(self):
        session_obj = self.env['op.session']
        data = []
        for session in self:
            start_date = session.start_date
            end_date = session.end_date
            for n in range((end_date - start_date).days + 1):
                curr_date = start_date + datetime.timedelta(n)
                for line in session.time_table_lines:
                    if int(line.day) == curr_date.weekday():
                        if line.timing_id:
                            h, m = line.timing_id.lesson_hour, line.timing_id.lesson_minute
                            duration = line.timing_id.duration
                            final_start_date = datetime.datetime.combine(curr_date, datetime.time(h, m))
                            final_end_date = final_start_date + datetime.timedelta(minutes=duration)
                        
                        curr_start_date = self.change_tz(final_start_date)
                        curr_end_date = self.change_tz(final_end_date)
                        data.append({
                            'faculty_id': line.faculty_id.id,
                            'subject_id': line.subject_id.id,
                            'course_id': session.course_id.id,
                            'batch_id': session.batch_id.id,
                            'timing_id': line.timing_id.id,
                            'classroom_id': line.classroom_id.id,
                            'start_datetime': curr_start_date.strftime("%Y-%m-%d %H:%M:%S"),
                            'end_datetime': curr_end_date.strftime("%Y-%m-%d %H:%M:%S"),
                        })
            if data:
                session_obj.create(data)
            return {'type': 'ir.actions.act_window_close'}

    def action_import_last_week(self):
        self.ensure_one()
        if not self.import_week_date:
            raise ValidationError(_("Выберите дату на неделе для импорта."))
        
        start_of_week = self.import_week_date - datetime.timedelta(days=self.import_week_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        sessions = self.env['op.session'].search([
            ('course_id', '=', self.course_id.id),
            ('batch_id', '=', self.batch_id.id),
            ('timetable_date', '>=', start_of_week),
            ('timetable_date', '<=', end_of_week),
            ('state', '!=', 'cancel'),
        ], order='timetable_date asc, start_datetime asc')
        
        if not sessions:
            raise ValidationError(_("Занятий не найдено."))
             
        lines_data = [(5, 0, 0)]
        seen = set()
        
        for session in sessions:
            day = str(session.timetable_date.weekday())
            timing_id = session.timing_id.id
            
            # --- ЛОГИКА ГЕОЛЕРНИНГА (ПОИСК СЛОТА ПО ВРЕМЕНИ) ---
            if not timing_id:
                # Берем время начала урока в часовом поясе пользователя
                local_dt = fields.Datetime.context_timestamp(session, session.start_datetime)
                # Ищем подходящий тайминг по часам и минутам
                match = self.env['op.timing'].search([
                    ('lesson_hour', '=', local_dt.hour),
                    ('lesson_minute', '=', local_dt.minute)
                ], limit=1)
                if match:
                    timing_id = match.id
            
            # Если даже после поиска слот не найден — пропускаем
            if not timing_id:
                continue
                
            if (day, timing_id) in seen:
                continue
            seen.add((day, timing_id))
            
            lines_data.append((0, 0, {
                'faculty_id': session.faculty_id.id,
                'subject_id': session.subject_id.id,
                'timing_id': timing_id,
                'classroom_id': session.classroom_id.id,
                'day': day,
            }))
        
        self.write({'time_table_lines': lines_data})
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }


class GenerateSessionLine(models.TransientModel):
    _name = 'gen.time.table.line'
    _description = 'Generate Time Table Lines'
    _rec_name = 'timing_id'

    gen_time_table = fields.Many2one(
        'generate.time.table', 'Time Table', required=True)
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
