# -*- coding: utf-8 -*-
{
    'name': 'Sales Commission',
    'version': '1.0',
    'summary': 'Gestión de comisiones para vendedores',
    'description': 'Registra y calcula comisiones para usuarios que participan en ventas.',
    'category': 'Sales',
    'author': 'Tu Empresa',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sales_commission_views.xml',
    ],
    'installable': True,
    'application':True,
    'license': 'LGPL-3',
}