"""Смоук-тесты op.session (ROST, 2026-09).

Прежний tests/test_timetable.py (2016, апстрим OpenEduCat) вызывал
методы, которых у модели давно нет (_compute_day, _compute_batch_users,
_check_date_time, onchange_course, notify_user, get_subject,
get_import_templates) и создавал wizard с удалённым course_id —
любой прогон тестов падал с AttributeError. Удалён, вместо него —

проверки актуального контракта модели:
- state machine кнопок (lecture_*);
- гейт пересчёта conflict-флагов: write({'state': ...}) НЕ пересчитывает
  соседей, изменение геометрии/отмена — пересчитывает (кейс Ермаковой);
- день недели и учебный год проставляются compute'ами.
"""
from odoo.tests import common
from odoo.exceptions import UserError


class TestSessionSmoke(common.TransactionCase):

    def _make_session(self, **over):
        Timing = self.env['op.timing']
        timing = Timing.search([], limit=1)
        vals = {
            'timing_id': timing.id,
            'start_datetime': '2026-09-14 06:00:00',
            'end_datetime': '2026-09-14 06:40:00',
            'faculty_id': self.env['op.faculty'].search([], limit=1).id,
            'batch_id': self.env['op.batch'].search([], limit=1).id,
            'subject_id': self.env['op.subject'].search([], limit=1).id,
            'course_id': self.env['op.course'].search([], limit=1).id,
        }
        vals.update(over)
        return self.env['op.session'].create(vals)

    def test_state_machine(self):
        s = self._make_session()
        s.lecture_confirm()
        self.assertEqual(s.state, 'confirm')
        s.lecture_start()
        self.assertEqual(s.state, 'start')
        s.lecture_done()
        self.assertEqual(s.state, 'done')
        s.lecture_edit()
        self.assertEqual(s.state, 'start')
        s.lecture_cancel()
        self.assertEqual(s.state, 'cancel')
        s.lecture_draft()
        self.assertEqual(s.state, 'draft')

    def test_day_and_year_computed(self):
        s = self._make_session()  # 2026-09-14 = понедельник
        self.assertEqual(s.timetable_date.strftime('%A').lower(), 'monday')
        self.assertTrue(s.days_id)
        # учебный год: сентябрь попадает в год 2026/2027 (тестовая БД
        # может иметь любой конкретный год — проверяем сам факт заполнения)
        self.assertTrue(s.academic_year_id)

    def test_state_write_skips_neighbor_recompute(self):
        """Гейт: state-переходы не запускают пересчёт флагов соседей."""
        s = self._make_session()
        called = []

        def _fake_recompute(recset):
            called.append(1)

        s.lecture_confirm()
        self.assertEqual(s.state, 'confirm')
        # прямой контракт: write state не меняет геометрию — соседи
        # не пересчитываются (функция не вызывается вообще).
        # Патчим метод инстанса на время вызова.
        env_session = type(s)
        orig = env_session._recompute_conflict_flags
        env_session._recompute_conflict_flags = _fake_recompute
        try:
            s.write({'state': 'start'})
            self.assertEqual(called, [], 'state write must skip recompute')
            # геометрия — должна вызвать (auto_reset добавляет второй
            # вызов: основной + после сброса conflict_override)
            s.write({'timetable_date': '2026-09-15'})
            self.assertEqual(len(called), 2,
                             'geometry write must recompute (2x with auto_reset)')
        finally:
            env_session._recompute_conflict_flags = orig

    def test_unlink_overlapping_pair(self):
        """Пакетное удаление пересекающихся уроков («Английский А/Б» на
        одном звонке): pre_neighbors не должны включать сами удаляемые
        записи — иначе после unlink пересчёт флагов падал MissingError
        («Запись не существует»), откатывая удаление целиком."""
        s1 = self._make_session(
            start_datetime='2026-09-14 06:00:00',
            end_datetime='2026-09-14 06:40:00')
        s2 = self._make_session(
            start_datetime='2026-09-14 06:00:00',
            end_datetime='2026-09-14 06:40:00')
        (s1 + s2).unlink()
        self.assertFalse(self.op_session.search_count(
            [('id', 'in', [s1.id, s2.id])]))

    def test_bad_time_raises(self):
        # start >= end отсекается раньше: пишем время ОТНОСИТЕЛЬНО
        # существующего, гарантируя end < start после сдвига на сутки.
        s = self._make_session()
        # отменённый урок не участвует в conflict-проверках, но
        # проверку порядка времени проходит первой же — двигаем в cancel
        # нельзя (skip), поэтому просто создаем новую запись с плохим временем
        with self.assertRaises(UserError):
            self._make_session(
                start_datetime='2026-10-01 07:00:00',
                end_datetime='2026-10-01 06:00:00',
                timing_id=False)


class TestImportLastWeek(common.TransactionCase):
    """Импорт в мастере «Создать расписание» (action_import_last_week).

    Параллельные уроки («Английский А»/«Английский Б» на одном звонке)
    должны попадать в таблицу мастера ОТДЕЛЬНЫМИ строками; отсекаются
    только полные дубли (тот же предмет и учитель в том же слоте —
    повтор в неделях периода импорта). Раньше ключ дедупликации был
    (день, слот) и второй урок пары молча терялся.
    """

    WEEK1_MONDAY = '2026-11-16'   # понедельник
    WEEK2_MONDAY = '2026-11-23'   # понедельник следующей недели

    def setUp(self):
        super().setUp()
        self.timing = self.env['op.timing'].create({
            'name': 'Тест слот', 'lesson_hour': 8, 'lesson_minute': 30,
            'duration': 40, 'sequence': 999})
        course = self.env['op.course'].create({
            'name': 'Тест курс импорта', 'code': 'TIMP'})
        self.batch = self.env['op.batch'].create({
            'name': 'Тест класс импорта', 'code': 'TIMP',
            'start_date': '2026-09-01', 'end_date': '2027-06-30',
            'course_id': course.id})
        self.subject_a = self.env['op.subject'].create({
            'name': 'Английский язык А (тест)', 'code': 'TIMPA'})
        self.subject_b = self.env['op.subject'].create({
            'name': 'Английский язык Б (тест)', 'code': 'TIMPB'})
        self.fac_a = self.env['op.faculty'].create({'name': 'Учитель А'})
        self.fac_b = self.env['op.faculty'].create({'name': 'Учитель Б'})

    def _make_session(self, subject, faculty, date):
        """Урок в понедельник на тестовый слот (время — середина дня UTC,
        чтобы timetable_date совпал с датой при любом часовом поясе)."""
        return self.env['op.session'].create({
            'timing_id': self.timing.id,
            'start_datetime': date + ' 06:00:00',
            'end_datetime': date + ' 06:40:00',
            'faculty_id': faculty.id,
            'batch_id': self.batch.id,
            'subject_id': subject.id,
            'course_id': self.batch.course_id.id,
        })

    def _make_wizard(self):
        return self.env['generate.time.table'].create({
            'batch_id': self.batch.id,
            'source_batch_id': self.batch.id,
            'import_start_date': self.WEEK1_MONDAY,
            'import_end_date': self.WEEK1_MONDAY,
            'start_date': '2026-12-07',
            'end_date': '2026-12-13',
        })

    def _make_pair(self, date):
        self._make_session(self.subject_a, self.fac_a, date)
        self._make_session(self.subject_b, self.fac_b, date)

    def test_parallel_lessons_imported(self):
        """Два урока на одном звонке импортируются двумя строками."""
        self._make_pair(self.WEEK1_MONDAY)
        wizard = self._make_wizard()
        res = wizard.action_import_last_week()

        lines = wizard.time_table_lines
        self.assertEqual(len(lines), 2,
                         'оба параллельных урока должны попасть в таблицу')
        self.assertEqual({l.subject_id for l in lines},
                         {self.subject_a, self.subject_b})
        # обе строки на одном (день, слот)
        self.assertEqual(len({(l.day, l.timing_id.id) for l in lines}), 1)
        # тост — успех без пропусков; упомянут параллельный слот
        self.assertEqual(res['tag'], 'display_notification')
        self.assertEqual(res['params']['type'], 'success')
        self.assertIn('Слотов с параллельными уроками: 1',
                      res['params']['message'])
        # next переоткрывает мастера с этой же записью; views обязателен —
        # клиентские действия не проходят серверный generate_views
        self.assertEqual(res['params']['next']['res_id'], wizard.id)
        self.assertEqual(res['params']['next']['views'], [[False, 'form']])

    def test_full_duplicates_skipped_with_warning(self):
        """Полные дубли (та же пара предмет+учитель в том же слоте второй
        недели) отсекаются, тост — warning с их числом."""
        self._make_pair(self.WEEK1_MONDAY)
        self._make_pair(self.WEEK2_MONDAY)
        wizard = self._make_wizard()
        wizard.import_end_date = self.WEEK2_MONDAY
        res = wizard.action_import_last_week()

        self.assertEqual(len(wizard.time_table_lines), 2)
        self.assertEqual(res['params']['type'], 'warning')
        self.assertIn('Пропущено полных дублей: 2', res['params']['message'])

    def test_confirm_warns_about_parallel_conflicts(self):
        """Пара из импорта на ПУСТОЙ период генерации: stat_parallel > 0 и
        has_soft_conflicts=True — иначе шаг подтверждения молчит, галочка
        «Утвердить конфликты автоматически» не показывается и вся пара
        создаётся красной (предыстория: «Английский А/Б» приходилось
        утверждать вручную)."""
        self._make_pair(self.WEEK1_MONDAY)
        wizard = self._make_wizard()
        wizard.action_import_last_week()

        action = wizard.act_gen_time_table()
        confirm = self.env['generate.time.table.confirm'].browse(
            action['res_id'])
        self.assertEqual(confirm.stat_new, 2)
        self.assertFalse(confirm.stat_existing)
        self.assertFalse(confirm.stat_overlap)
        self.assertEqual(confirm.stat_parallel, 2)
        self.assertTrue(confirm.has_soft_conflicts)

    def test_reimport_keeps_parallel_toggle_in_overlap_mode(self):
        """Повторный импорт того же расписания: режим overlap (совпадающие
        заменяются), но галочка автоутверждения должна остаться видимой —
        пары «А/Б» конфликтуют внутри генерации в ЛЮБОМ режиме
        (has_parallel_conflicts)."""
        self._make_pair(self.WEEK1_MONDAY)
        wizard = self._make_wizard()
        wizard.action_import_last_week()
        # период генерации = период с уже существующей парой
        wizard.start_date = self.WEEK1_MONDAY
        wizard.end_date = '2026-11-22'
        action = wizard.act_gen_time_table()
        confirm = self.env['generate.time.table.confirm'].browse(
            action['res_id'])
        self.assertEqual(confirm.mode, 'overlap')
        self.assertEqual(confirm.stat_overlap, 2)
        self.assertEqual(confirm.stat_parallel, 2)
        self.assertTrue(confirm.has_soft_conflicts)
        self.assertTrue(confirm.has_parallel_conflicts)

