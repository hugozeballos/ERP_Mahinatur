from odoo import models, fields, api

class TourParticipant(models.Model):
    _name = 'tour.participant'
    _inherit = 'mail.thread'
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
    is_overbooked = fields.Boolean(
        string="Sobrevendido",
        compute="_compute_is_overbooked",
        store=True)

    #Calcular sobrevendido
    @api.depends('tour_id', 'tour_id.participants_ids')
    def _compute_is_overbooked(self):
        for rec in self:
            tour = rec.tour_id
            if not tour or not tour.max_capacity:
                rec.is_overbooked = False
                continue
            participants = tour.participants_ids.sorted('id')
            allowed = participants[:tour.max_capacity]
            rec.is_overbooked = rec not in allowed

    def action_open_move_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mover Participante',
            'res_model': 'tour.participant.move.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_participant_id': self.id,
                'active_id': self.id,
            }
        }

