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
    index_in_tour = fields.Integer(string='#', compute='_compute_index_in_tour', store=False)


    tour_id = fields.Many2one('tour.minimal', string='Tour', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de Venta')
    is_overbooked = fields.Boolean(
        string="Sobrevendido",
        compute="_compute_is_overbooked",
        store=True)
    
    flight_in_id = fields.Many2one('tour.flight', string='Vuelo In')
    flight_out_id = fields.Many2one('tour.flight', string='Vuelo Out')
    hotel_id = fields.Many2one('res.partner', string='Hotel', domain="[('is_hotel','=',True)]")

    lunch_badge = fields.Html(
        string='Almuerzo',
        compute='_compute_lunch_badge',
        sanitize=False, store=False)
    
    def action_cycle_lunch(self):
        order = [False, 'lunch_normal', 'lunch_veg', 'lunch_extra', 'menu_rest']
        for r in self:
            cur = r.tipo_almuerzo or False
            nxt = order[(order.index(cur) + 1) % len(order)]
            r.write({'tipo_almuerzo': nxt, 'almuerzo': bool(nxt)})

    @api.depends('tour_id', 'tour_id.participants_ids')
    def _compute_index_in_tour(self):
        for rec in self:
            if rec.tour_id:
                ids = rec.tour_id.participants_ids.ids
                rec.index_in_tour = ids.index(rec.id) + 1 if rec.id in ids else 0
            else:
                rec.index_in_tour = 0

    #Calcular sobrevendido
    @api.depends('tour_id', 'tour_id.participants_ids')
    def _compute_is_overbooked(self):
        for rec in self:
            tour = rec.tour_id
            if not tour or not tour.max_capacity:
                rec.is_overbooked = False
                continue
            participants = tour.participants_ids
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

    @api.onchange('tipo_almuerzo')
    def _onchange_tipo_almuerzo(self):
        for rec in self:
            rec.almuerzo = bool(rec.tipo_almuerzo)

    @api.onchange('almuerzo')
    def _onchange_almuerzo(self):
        for rec in self:
            if not rec.almuerzo:
                rec.tipo_almuerzo = False

    @api.depends('tipo_almuerzo')
    def _compute_lunch_badge(self):
        label_map = {
            'lunch_normal': 'Box Lunch normal',
            'lunch_veg':    'Box Lunch vegetariano',
            'lunch_extra':  'Box Lunch extra',
            'menu_rest':    'Almuerzo/Cena menú + TRF',
        }
        class_map = {
            'lunch_normal': 'text-bg-danger',   # rojo
            'lunch_veg':    'text-bg-success',  # verde
            'lunch_extra':  'text-bg-warning',  # amarillo
            'menu_rest':    'text-bg-primary',  # azul (ver nota morado)
        }
        for r in self:
            key = r.tipo_almuerzo
            r.lunch_badge = (
                f'<span class="badge {class_map[key]}">{label_map[key]}</span>'
            ) if key else ''
