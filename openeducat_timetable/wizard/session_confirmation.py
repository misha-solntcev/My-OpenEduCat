from odoo import models, api, fields

class SessionConfirmation(models.TransientModel):
    _name = "session.confirmation"
    _description = "Wizard for Multiple Session Actions"

    action_type = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),                
    ], string="Тип действия")

    def state_draft(self):
        """Массовый возврат в статус Черновик"""
        active_ids = self.env.context.get('active_ids', [])
        # Возвращаем в черновик всё, что не является черновиком
        lines = self.env['op.session'].search([
            ('id', 'in', active_ids),
            ('state', '!=', 'draft')
        ])
        for line in lines:
            line.lecture_draft()

    def state_confirmation(self):
        """Массовое утверждение (из черновика или отмены)"""
        active_ids = self.env.context.get('active_ids', [])
        lines = self.env['op.session'].search([
            ('id', 'in', active_ids),
            ('state', 'in', ['draft', 'cancel'])
        ])
        for line in lines:
            line.lecture_confirm()

    def state_cancel(self):
        """Массовая отмена"""
        active_ids = self.env.context.get('active_ids', [])
        lines = self.env['op.session'].search([
            ('id', 'in', active_ids),
            ('state', '!=', 'done')
        ])
        for line in lines:
            line.lecture_cancel()

    def state_done(self):
        """Массовое завершение"""
        active_ids = self.env.context.get('active_ids', [])
        lines = self.env['op.session'].search([
            ('id', 'in', active_ids),
            ('state', '=', 'start')
        ])
        for line in lines:
            line.lecture_done()

    def state_draft(self):
        """Массовый возврат в статус Черновик"""
        active_ids = self.env.context.get('active_ids', [])
        # Возвращаем в черновик всё, что не является черновиком
        lines = self.env['op.session'].search([
            ('id', 'in', active_ids),
            ('state', '!=', 'draft')
        ])
        for line in lines:
            line.lecture_draft()