# Part of the OMPAY payment provider for Odoo.

{
    'name': "OMPAY Payment Gateway",
    'version': '19.0.2.0.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "Accept card payments in Omani Rial through OMPAY.",
    # Non-empty string so Odoo does not fall back to the README; the Apps
    # listing is rendered from static/description/index.html instead.
    'description': " ",
    'author': "OMPAY",
    'maintainer': "OMPAY",
    'website': "https://ompay.om",
    'support': "pgsupport@ompay.com",
    'images': [
        'static/description/banner.png',
        'static/description/screenshot-payment-page.png',
        'static/description/screenshot-payment-success.png',
    ],
    'depends': ['payment'],
    'data': [
        'views/ompay_tp_plugin_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ompay_tp_plugin/static/src/js/payment_form.js',
            'ompay_tp_plugin/static/src/scss/ompay_tp_plugin.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
