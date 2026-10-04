# Part of the OMPAY payment provider for Odoo.

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

# Keys that must never reach a log file.
#
# Odoo logs the body of every API request it sends, and `payment`'s own
# SENSITIVE_KEYS set is empty by default: each provider is responsible for
# declaring its own. Without this, the Merchant Hosted flow would write full card
# numbers and CVVs into the server log in plain text, which PCI DSS forbids.
#
# Updating the shared set is what makes the masking apply, because the logging
# happens inside the `payment` module, not here.
SENSITIVE_KEYS = {
    'card',
    'number',
    'cvv',
    'exp_month',
    'exp_year',
    'holder_name',
    'token',
    'saved_card',
    'dpan',
    'cryptogram',
}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

# API base URLs. Odoo's native provider `state` decides which one is used:
# `enabled` means live, anything else (`test`) means sandbox.
API_URLS = {
    'production': 'https://api.truepay.ompay.om/api/v1',
    'sandbox': 'https://api.sandbox.truepay.ompay.om/api/v1',
}

# Endpoints of the OMPAY API.
ENDPOINT_BANK_HOSTED = '/transactions/bank-hosted'
ENDPOINT_MERCHANT_HOSTED = '/transactions/merchant-hosted'
ENDPOINT_INQUIRY = '/transactions/inquiry'
ENDPOINT_REFUND = '/transactions/%s/refund'

# Mapping of OMPAY transaction statuses to Odoo payment transaction states.
# OMPAY lifecycle: PENDING -> PROCESSING -> SUCCESSFUL | FAILED.
PAYMENT_STATUS_MAPPING = {
    'pending': ('PENDING', 'PROCESSING'),
    'done': ('SUCCESSFUL',),
    'error': ('FAILED',),
}

# Currencies that use three decimal places rather than the usual two. OMPAY
# settles in Omani Rial, which is a three-decimal currency; sending a
# two-decimal amount would silently under- or over-charge.
THREE_DECIMAL_CURRENCIES = ('OMR', 'BHD', 'KWD', 'JOD', 'TND', 'IQD', 'LYD')

# No hard-coded currency allowlist.
#
# Which currencies OMPAY will settle is account-specific, and the API does not
# reject an unfamiliar currency when the transaction is created — a sandbox probe
# with USD was accepted. Guessing a list here would silently hide the provider at
# checkout for a currency the merchant is actually entitled to use, which is far
# harder to diagnose than an API error. Merchants restrict currencies with Odoo's
# native "Available Currencies" field on the provider instead.

# Payment methods enabled on the provider by default.
DEFAULT_PAYMENT_METHOD_CODES = (
    'card',
)

# Error codes returned by the API that deserve a clearer message than the raw
# one, because the merchant (not the shopper) needs to act on them.
ERROR_MESSAGES = {
    'MERCHANT_CAPABILITY_DISABLED': (
        "This payment flow, or the card's BIN range, is not enabled on your OMPAY account."
        " Ask OMPAY to enable it."
    ),
    'DUPLICATE_ENTRY': (
        "A transaction with this reference already exists at OMPAY."
    ),
    'INVALID_CREDENTIALS': (
        "OMPAY rejected the API key or secret. Check that the credentials match the"
        " environment: a provider in Test Mode needs sandbox keys, and an enabled"
        " provider needs production keys."
    ),
}
