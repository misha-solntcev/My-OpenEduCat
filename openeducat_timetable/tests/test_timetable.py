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
