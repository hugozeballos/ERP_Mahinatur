# models/hr_employee_extend.py
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    languages_spoken = fields.Many2many(
        'res.lang',
        'hr_employee_res_lang_rel',
        'employee_id',
        'lang_id',
        string="Idiomas hablados",
        help="Idiomas que domina este empleado"
    )