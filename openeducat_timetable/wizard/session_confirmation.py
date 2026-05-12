from odoo import models, api, fields

class SessionConfirmation(models.TransientModel):
    _name = "session.confirmation"
    _description = "Массовые действия с уроками"

    action_type = fields.Selection([
        ('draft', 'В черновик'), 
        ('confirm', 'Утвердить'),
        ('done', 'Завершить'), 
        ('cancel', 'Отменить')
    ], string="Тип действия")

    def _process(self, method_name):
        active_ids = self.env.context.get('active_ids', [])
        sessions = self.env['op.session'].browse(active_ids)
        if sessions:
            getattr(sessions, method_name)()

    def state_draft(self): self._process('lecture_draft')
    def state_confirmation(self): self._process('lecture_confirm')
    def state_done(self): self._process('lecture_done')
    def state_cancel(self): self._process('lecture_cancel')