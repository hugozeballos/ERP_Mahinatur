from odoo import models, fields

class TicketDailyCounter(models.Model):
    _name = 'ticket.daily.counter'
    _description = 'Contador Diario de Tickets'

    date = fields.Date(string="Fecha", required=True)
    national_qty = fields.Integer(string="Tickets Nacionales", default=0)
    foreigner_qty = fields.Integer(string="Tickets Extranjeros", default=0)
    sale_order_ids = fields.Many2many('sale.order', string="Órdenes de Venta")
    partner_id = fields.Many2one('res.partner', string="Cliente")
