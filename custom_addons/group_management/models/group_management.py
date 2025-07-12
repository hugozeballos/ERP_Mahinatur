from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class GroupManagement(models.Model):
    _name = 'group.management'
    _description = 'Group Management'

    name              = fields.Char(string='Reference', required=True,
                                   default=lambda self: self.env['ir.sequence'].next_by_code('group.management'))
    date              = fields.Date(string='Date', required=True)
    partner_id        = fields.Many2one('res.partner', string='Customer', required=True)
    state             = fields.Selection([('draft','Draft'),('confirmed','Confirmed')], default='draft')
    activity_line_ids = fields.One2many('group.activity.line', 'group_id', string='Activities')
    group_size = fields.Integer(string='Tamaño del Grupo', required=True,
                                help="Número total de personas en este grupo")
    language_id = fields.Many2one(
        'res.lang',
        string='Idioma del grupo',
        default=lambda self: self.env.lang,
        required=True
    )
    @api.constrains('activity_line_ids')
    def _check_no_overlap(self):
        for rec in self:
            lines = rec.activity_line_ids.sorted(key=lambda l: l.scheduled_from)
            for i in range(len(lines)-1):
                if lines[i+1].scheduled_from < lines[i].scheduled_to:
                    raise ValidationError(
                      f"Activities '{lines[i].template_id.name}' and "
                      f"'{lines[i+1].template_id.name}' overlap."
                    )

    def action_confirm_group(self):
        Tour = self.env['tour.minimal']
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']
        Product = self.env['product.product']

        for rec in self:
            if not rec.activity_line_ids:
                raise UserError(("Añade al menos una actividad."))

            # Buscar el producto "Grupo"
            group_product = Product.search([('name', '=', 'Grupo Turistico')], limit=1)
            if not group_product:
                raise UserError("El producto 'Grupo' no está creado. Por favor crea uno con ese nombre.")

            # Crear la orden de venta
            order = SaleOrder.create({
                'partner_id': rec.partner_id.id,
                'origin': rec.name,
            })

            total_price = 0.0

            for line in rec.activity_line_ids:
                new_tour = Tour.create({
                    'name':         f"{rec.name} – {line.template_id.name}",
                    'date_start':   line.scheduled_from,
                    'date_end':     line.scheduled_to,
                    'max_capacity': rec.group_size,
                    'group_id':     rec.id,
                    'template_id':  line.template_id.id,
                    'state':        'draft',
                    'requires_cook': line.template_id.requires_cook,
                    'language_id':  rec.language_id.id

                })

                participants_vals = [(0, 0, {'name': f'Participante {i+1}'}) for i in range(rec.group_size)]
                new_tour.write({'participants_ids': participants_vals})

                # Sumar precios
                total_price += line.template_id.price_per_seat * rec.group_size

            # Crear una sola línea de venta con el producto "Grupo"
            SaleOrderLine.create({
                'order_id': order.id,
                'name': f'Grupo: {rec.name}',
                'product_id': group_product.id,
                'product_uom_qty': 1,
                'price_unit': total_price,
            })

            rec.state = 'confirmed'
