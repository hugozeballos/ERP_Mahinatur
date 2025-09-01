# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_tour_ticket = fields.Boolean(string="Es Cupo de Tour")
    tour_id = fields.Many2one('tour.minimal', string="Tour Asociado")
    is_private_tour = fields.Boolean(
        string="Cupo de Tour Privado",
        help="Si está activo, al vender este producto se tratará como reserva privada."
    )
    is_tour_addon = fields.Boolean(string='Es add-on de tour', required=False, default=False)
    addon_code = fields.Selection([
        ('lunch_normal', 'Box Lunch normal'),
        ('lunch_veg',    'Box Lunch vegetariano'),
        ('lunch_extra',  'Box Lunch extra'),
        ('menu_rest',    'Almuerzo/Cena menú + TRF'),
    ], string='Tipo de add-on', required=False)
    language_id = fields.Many2one(
        'res.lang',
        string='Idioma del tour',
        help='Idioma principal para este tour (si aplica).'
    )

    provider_id = fields.Many2one(
        'res.partner',
        string='Proveedor del tour',
        help="Proveedor asociado a este tour externo.")
    # Campos requeridos para POS
    available_in_pos = fields.Boolean(string="Disponible en Punto de Venta", default=True)
    pos_categ_id = fields.Many2one('pos.category', string="Categoría POS")
    is_external = fields.Boolean(string='Producto Externo', help='Si está marcado, se usa el wizard vacío')
    service_kind = fields.Selection(
        [('sib', 'SIB (regular con cupos)'), ('private', 'Privado (crear salida)'), ('external', 'Externo (actividad sin tour)')],
        string='Tipo de servicio',
        help="Diferencia si este producto tour se opera como SIB (cupos existentes) o Privado (se crea salida)."
    )
    tour_type_id = fields.Many2one('tour.type', string='Tipo de tour')
