{  
    'name': 'Group Management',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Manage activity groups and bulk generate tour bookings',
    'description': 'Create groups of activities and generate tour instances.',
    'author': 'Tu Empresa',
    'depends': ['base', 'tour_minimal_odoo17'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/group_management_views.xml',
        'views/activity_template_views.xml',
        'views/tour_minimal_inherit_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}