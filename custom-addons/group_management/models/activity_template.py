from odoo import models, fields

class ActivityTemplate(models.Model):
    _name = 'group.activity.template'
    _description = 'Activity Template'

    name         = fields.Char(string='Name', required=True)
    activity_type= fields.Selection([
        ('transfer_in', 'Transfer In'),
        ('transfer_out','Transfer Out'),
        ('full_day',   'Full Day'),
        ('Half_day_AM',   'Half Day AM'),
        ('Half_day_PM',   'Half Day PM'),
        ('Buceo',   'Buceo'),
        ('Cavalgata_Terevaka', 'Cavalgata Terevaka'),
        ('Cavalgata_cuevas', 'Cavalgata Cuevas'),
        ('Almuerzo_anakena', 'Almuerzo Anakena'),
        ('Almuerzo_parcela', 'Almuerzo Parcela'),
        ('Atardecer_Tahai', 'Atardecer Tahai'),
        ('Ticket', 'Ticket'),
    ], string='Type', required=True)
    language     = fields.Selection([('en','English'),('es','Spanish')], string='Language', default='en')
    guide_id     = fields.Many2one('hr.employee',   string='Guide')
    driver_id    = fields.Many2one('hr.employee',   string='Driver')
    vehicle_id   = fields.Many2one('fleet.vehicle', string='Vehicle')
    price        = fields.Monetary(string='Price')
    default_duration = fields.Float(
        string='Duración (horas)',
        help="Duración estándar de esta actividad"
    )
    capacity   = fields.Integer(string='Capacidad personas en grupo')
    price_per_seat = fields.Monetary(string='Precio por plaza')
    currency_id  = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    requires_guide     = fields.Boolean(string='Requiere Guía', default=False)
    requires_transport = fields.Boolean(string='Requiere Transporte', default=False)
    requires_cook = fields.Boolean(string="Requiere Cocinero", default=False)
    requires_waiter = fields.Boolean(string="Requiere Garzón", default=False)
    #cook_id     = fields.Many2one('hr.employee',   string='Cook')
    #waiters_id    = fields.Many2one('hr.employee',   string='Waiters')