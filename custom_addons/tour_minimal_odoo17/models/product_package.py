# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_tour_package = fields.Boolean(string="Es paquete de tours")
    package_line_ids = fields.One2many(
        'tour.package.line', 'package_id', string='Componentes del paquete'
    )

    @api.constrains('is_tour_package', 'package_line_ids')
    def _check_package_has_components(self):
        for tmpl in self:
            if tmpl.is_tour_package and not tmpl.package_line_ids:
                raise ValidationError(_("Un paquete de tours debe tener al menos un componente."))

class TourPackageLine(models.Model):
    _name = 'tour.package.line'
    _description = 'Componente de paquete de tours'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    package_id = fields.Many2one(
        'product.template', string='Paquete', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', string='Producto tour', required=True,
        domain="[('product_tmpl_id.is_tour_ticket','=',True)]"
    )
    note = fields.Char(string='Nota', help="Observación operativa (opcional).")
    

    @api.constrains('product_id')
    def _check_component_is_tour_and_not_package(self):
        for line in self:
            if not line.product_id or not line.product_id.product_tmpl_id:
                continue
            tmpl = line.product_id.product_tmpl_id
            # Debe ser un producto tour válido de tu módulo
            if not tmpl.is_tour_ticket:
                raise ValidationError(_("El componente debe ser un producto de tour (Es Cupo de Tour)."))
            # No permitir recursividad: un paquete no puede referenciar otro paquete
            if tmpl.is_tour_package:
                raise ValidationError(_("No se permite usar un paquete como componente de otro paquete."))
            
