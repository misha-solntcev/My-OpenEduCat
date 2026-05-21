from odoo import fields, models # type: ignore


class OpTiming(models.Model):
    _name = "op.timing"
    _description = "Period (Lesson Slot)"
    _order = "sequence"

    name = fields.Char('Name', size=32, required=True)
    lesson_hour = fields.Integer('Hour', required=True)
    lesson_minute = fields.Integer('Minute', required=True)
    duration = fields.Integer('Duration (Minutes)', default=40)
    sequence = fields.Integer('Sequence', default=10)

    def name_get(self):
        result = []
        for rec in self:
            start = f"{rec.lesson_hour:02d}:{rec.lesson_minute:02d}"
            total_min = rec.lesson_hour * 60 + rec.lesson_minute + rec.duration
            h_e, m_e = divmod(total_min, 60)
            end = f"{int(h_e):02d}:{int(m_e):02d}"
            result.append((rec.id, f"{rec.name} ({start} - {end})"))
        return result
