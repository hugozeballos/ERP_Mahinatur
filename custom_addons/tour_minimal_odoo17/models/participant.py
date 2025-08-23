from odoo import models, fields

class TourParticipant(models.Model):
    _name = 'tour.participant'
    _description = 'Participante del tour'

    name = fields.Char(string='Nombre del Participante', required=True)
    almuerzo = fields.Boolean(string='¿Incluir almuerzo?')
    tipo_almuerzo = fields.Selection([
        ('lunch_normal', 'Box Lunch normal'),
        ('lunch_veg',    'Box Lunch vegetariano'),
        ('lunch_extra',  'Box Lunch extra'),
        ('menu_rest',    'Almuerzo/Cena menú + TRF'),
    ], string='Tipo de Almuerzo')

    tour_id = fields.Many2one('tour.minimal', string='Tour', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de Venta')
