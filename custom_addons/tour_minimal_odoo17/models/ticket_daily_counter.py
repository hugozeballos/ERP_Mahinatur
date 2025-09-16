from odoo import models, fields, api

class TicketDailyCounter(models.Model):
    _name = 'ticket.daily.counter'
    _description = 'Contador Diario de Tickets'

    date = fields.Date(string="Fecha", required=True)
    national_qty = fields.Integer(string="Tickets Nacionales", default=0)
    foreigner_qty = fields.Integer(string="Tickets Extranjeros", default=0)
    sale_order_ids = fields.Many2many('sale.order', string="Órdenes de Venta")
    partner_id = fields.Many2one('res.partner', string="Cliente")
    ticket_line_ids = fields.One2many('ticket.counter.line', 'counter_id', string="Detalle de Tickets")
    name = fields.Char(string='Resumen', compute='_compute_name', store=True)

    @api.depends('national_qty', 'foreigner_qty')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Nac: {rec.national_qty} - Ext: {rec.foreigner_qty}"


class TicketCounterLine(models.Model):
    _name = 'ticket.counter.line'
    _description = 'Detalle de tickets por día y tipo'

    counter_id = fields.Many2one('ticket.daily.counter', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta')
    partner_id = fields.Many2one(related='sale_order_id.partner_id', store=True)
    ticket_type = fields.Selection([
        ('nac', 'Nacional'),
        ('ext', 'Extranjero')
    ], string="Tipo de Ticket")
    qty = fields.Integer(string='Cantidad de Tickets')
