from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GroupActivityBundle(models.Model):
    _name = 'group.activity.bundle'
    _description = 'Plantilla de Grupo (Paquete de Actividades)'
    _order = 'name'

    name = fields.Char(required=True)
    line_ids = fields.One2many('group.activity.bundle.line', 'bundle_id', string='Actividades')

    # NUEVO: tramos de precio por persona
    tier_ids = fields.One2many('group.activity.bundle.tier', 'bundle_id', string='Precios por grupo')


class GroupActivityBundleLine(models.Model):
    _name = 'group.activity.bundle.line'
    _description = 'Línea de Plantilla de Grupo'

    bundle_id = fields.Many2one('group.activity.bundle', ondelete='cascade')
    template_id = fields.Many2one('group.activity.template', string='Actividad base', required=True)

    # Si quieres permitir sobreescribir precio por plaza a nivel de plantilla de grupo:
    price_per_seat_override = fields.Monetary(string='Precio por plaza (override)')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id.id)

    # (Opcional) Autoprogramación por offsets:
    day_offset = fields.Integer(string='Día +N desde inicio del grupo')
    start_time = fields.Float(string='Hora inicio (0-24)', required=True)
    end_time = fields.Float(string='Hora fin (0-24)')

    #Día relativo (1 = día de inicio del grupo)
    day_number = fields.Integer(string='Día (N)', default=1,
                                help='1 = día de inicio del grupo, 2 = segundo día, etc.')


    # Opcional: pequeña validación
    @api.constrains('day_number', 'start_time', 'end_time')
    def _check_day_and_time(self):
        for rec in self:
            if rec.day_number and rec.day_number < 1:
                raise ValidationError(_('El día debe ser 1 o mayor.'))
            if rec.start_time and (rec.start_time < 0 or rec.start_time >= 24):
                raise ValidationError(_('La hora de inicio debe estar entre 0 y 24.'))
            if rec.end_time and (rec.end_time < 0 or rec.end_time > 24):
                raise ValidationError(_('La hora de fin debe estar entre 0 y 24.'))
            if rec.start_time and rec.end_time and rec.end_time <= rec.start_time:
                raise ValidationError(_('La hora de fin debe ser mayor que la hora de inicio.'))

class GroupActivityBundleTier(models.Model):
    _name = 'group.activity.bundle.tier'
    _description = 'Tramo de precio por persona para una plantilla'
    _order = 'min_people asc'

    bundle_id = fields.Many2one('group.activity.bundle', required=True, ondelete='cascade')
    min_people = fields.Integer(string='Desde (personas)', required=True)
    max_people = fields.Integer(string='Hasta (personas)', help='Vacío = sin tope (o más)')
    price_per_person = fields.Monetary(string='Precio por persona', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)


    @api.constrains('min_people', 'max_people', 'bundle_id')
    def _check_ranges(self):
        for rec in self:
            if rec.min_people <= 0:
                raise ValidationError(_('El mínimo de personas debe ser mayor a 0.'))
            if rec.max_people and rec.max_people < rec.min_people:
                raise ValidationError(_('El máximo debe ser mayor o igual al mínimo.'))
            # Validar solapes dentro del mismo bundle
            domain = [('bundle_id', '=', rec.bundle_id.id), ('id', '!=', rec.id)]
            other_tiers = self.search(domain)
            for other in other_tiers:
                # Interpretación: None = infinito
                o_min = other.min_people
                o_max = other.max_people or 10**9
                r_min = rec.min_people
                r_max = rec.max_people or 10**9
                # solapa si intersecan
                if not (r_max < o_min or r_min > o_max):
                    raise ValidationError(_('Los tramos no pueden solaparse. Revise los rangos.'))
