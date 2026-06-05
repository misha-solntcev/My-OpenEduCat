from odoo import models, fields, api
import datetime
from datetime import timedelta
import pytz


class OpTimeMixin(models.AbstractModel):
    _name = 'op.time.mixin'
    _description = 'Утилиты синхронизации времени и расписания'

    # --- 1. БАЗОВЫЕ НАСТРОЙКИ ---
    def _get_school_timezone(self):
        """Школа физически находится в Москве. Сетка уроков привязана к МСК."""
        return 'Europe/Moscow'

    def _convert_to_local(self, utc_datetime):
        """Переводит UTC из базы в локальное время школы (МСК)"""
        if not utc_datetime:
            
            return False
        tz = self._get_school_timezone()
        return fields.Datetime.context_timestamp(self.with_context(tz=tz), utc_datetime)

    def _get_local_today(self):
        """Возвращает текущую дату школы (МСК)"""
        return fields.Date.context_today(self.with_context(tz=self._get_school_timezone()))

    # --- 2. ГЛАВНЫЙ МАСТЕР-СИНХРОНИЗАТОР ---
    def _sync_time_values(self, start_dt=None, timing_id=None, date_val=None):
        """
        Универсальный метод синхронизации полей времени.
        Сценарий А: Передали время (start_dt) -> Находим ближайший Урок (Слот).
        Сценарий Б: Передали Урок (timing_id) и Дату -> Вычисляем Время начала/конца.
        """
        # 0. Загружаем сетку звонков
        all_timings = self.env['op.timing'].sudo().search([])
        if not all_timings:
            return {}

        school_tz_name = self._get_school_timezone()
        school_tz = pytz.timezone(school_tz_name)

        # ПЕРЕМЕННЫЕ ДЛЯ РАСЧЕТА (в локальном Московском времени)
        dt_school_final = False
        timing_record = False

        # --- СЦЕНАРИЙ А: Изменили время начала (Магнит) ---
        if start_dt:
            # Превращаем в UTC объект с зоной
            if isinstance(start_dt, str):
                start_dt = fields.Datetime.to_datetime(start_dt)
            if not start_dt.tzinfo:
                start_dt = pytz.utc.localize(start_dt)

            # Переводим в Москву
            dt_school = start_dt.astimezone(school_tz)
            drop_mins = dt_school.hour * 60 + dt_school.minute
            
            # Ищем ближайший Московский слот
            timing_record = min(all_timings, key=lambda t: abs(drop_mins - (t.lesson_hour * 60 + t.lesson_minute)))
            
            # Формируем точное время по сетке
            dt_school_final = dt_school.replace(
                hour=timing_record.lesson_hour, 
                minute=timing_record.lesson_minute, 
                second=0, microsecond=0
            )

        # --- СЦЕНАРИЙ Б: Изменили Урок или Дату в форме ---
        elif timing_id and date_val:
            timing_record = all_timings.filtered(lambda t: t.id == timing_id)
            if not timing_record:
                return {}
            
            # Собираем Московское время из Даты и Часов слота
            naive_date = fields.Date.to_date(date_val)
            dt_school_final = school_tz.localize(datetime.datetime.combine(
                naive_date,
                datetime.time(timing_record.lesson_hour, timing_record.lesson_minute)
            ))
        
        else:
            return {}

        # --- ФИНАЛЬНАЯ КОНВЕРТАЦИЯ В UTC ДЛЯ БАЗЫ ---
        # Избавляемся от смещения для корректной работы localize
        utc_start = school_tz.localize(dt_school_final.replace(tzinfo=None)).astimezone(pytz.utc).replace(tzinfo=None)
        
        return {
            'timing_id': timing_record.id,
            'start_datetime': utc_start,
            'end_datetime': utc_start + timedelta(minutes=timing_record.duration),
            'timetable_date': dt_school_final.date()
        }