# Part of the OMPAY payment provider for Odoo.

from . import controllers
from . import models

from odoo.addons.payment import reset_payment_provider, setup_provider


def post_init_hook(env):
    setup_provider(env, 'ompay')


def uninstall_hook(env):
    reset_payment_provider(env, 'ompay')
