# Part of the OMPAY payment provider for Odoo.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_ompay import const


_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('ompay', "OMPAY")], ondelete={'ompay': 'set default'}
    )
    ompay_api_key = fields.Char(
        string="OMPAY API Key",
        help="Sent as the OMPAY-API-Key header. Sandbox and production use different keys.",
        required_if_provider='ompay',
        copy=False,
    )
    ompay_api_secret = fields.Char(
        string="OMPAY API Secret",
        help="Sent as the OMPAY-API-Secret header. Never share this value.",
        required_if_provider='ompay',
        copy=False,
        groups='base.group_system',
    )
    ompay_flow = fields.Selection(
        string="Checkout Flow",
        help="Bank Hosted redirects the customer to an OMPAY page and keeps card data off your"
             " server (PCI DSS SAQ A). Merchant Hosted renders the card form on your checkout and"
             " sends the card through your server (PCI DSS SAQ D).",
        selection=[
            ('bank_hosted', "Bank Hosted (redirect)"),
            ('merchant_hosted', "Merchant Hosted (card form on your site)"),
        ],
        default='bank_hosted',
        required_if_provider='ompay',
    )
    ompay_pci_ack = fields.Boolean(
        string="PCI DSS SAQ D Confirmed",
        help="Required before the Merchant Hosted flow will run. Only tick this if your business"
             " has completed PCI DSS SAQ D.",
        copy=False,
    )

    # === CONSTRAINT METHODS === #

    @api.constrains('ompay_flow', 'ompay_pci_ack', 'state')
    def _check_ompay_merchant_hosted_is_acknowledged(self):
        """Refuse to enable the Merchant Hosted flow without a PCI acknowledgement.

        Handling raw card numbers places the merchant in the heaviest PCI compliance
        tier. Making this an explicit, deliberate step keeps a merchant from switching
        into it without realising the obligation they take on.
        """
        for provider in self.filtered(lambda p: p.code == 'ompay'):
            if provider.ompay_flow == 'merchant_hosted' and not provider.ompay_pci_ack:
                raise ValidationError(_(
                    "The Merchant Hosted flow sends full card numbers through your server, which"
                    " requires PCI DSS SAQ D compliance. Confirm compliance on the OMPAY provider"
                    " form, or use the Bank Hosted flow instead."
                ))

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'ompay').update({
            'support_refund': 'partial',
        })

    # === BUSINESS METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != 'ompay':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _should_build_inline_form(self, is_validation=False):
        """Override of `payment` to build an inline form only for Merchant Hosted.

        Bank Hosted has nothing to collect on the store: the customer is sent
        straight to the OMPAY payment page.
        """
        if self.code != 'ompay':
            return super()._should_build_inline_form(is_validation=is_validation)
        return self.ompay_flow == 'merchant_hosted'

    def _ompay_is_production(self):
        """Return whether the provider points at the live API.

        Odoo's own provider state is the single source of truth here, so there is
        no separate environment setting to keep in sync with it.

        Note: `self.ensure_one()`

        :return: Whether live credentials and URLs should be used.
        :rtype: bool
        """
        self.ensure_one()
        return self.state == 'enabled'

    @staticmethod
    def _ompay_round_amount(amount, currency_code):
        """Round an amount to the precision the currency expects.

        :param float amount: The amount to round.
        :param str currency_code: The ISO-4217 code of the currency.
        :return: The rounded amount.
        :rtype: float
        """
        decimals = 3 if (currency_code or '').upper() in const.THREE_DECIMAL_CURRENCIES else 2
        return round(float(amount), decimals)

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'ompay':
            return super()._build_request_url(endpoint, **kwargs)
        base_url = const.API_URLS['production' if self._ompay_is_production() else 'sandbox']
        return f'{base_url}{endpoint}'

    def _build_request_headers(self, *args, **kwargs):
        """Override of `payment` to build the request headers.

        OMPAY identifies the account by these two headers alone; there is no
        merchant id to send.
        """
        if self.code != 'ompay':
            return super()._build_request_headers(*args, **kwargs)
        return {
            'OMPAY-API-Key': self.ompay_api_key or '',
            'OMPAY-API-Secret': self.ompay_api_secret or '',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to unwrap the OMPAY response envelope.

        Every OMPAY response is shaped `{"success": true, "data": {...}}`. Callers
        want the inner payload, so it is unwrapped once here rather than at each
        call site.
        """
        if self.code != 'ompay':
            return super()._parse_response_content(response, **kwargs)

        payload = response.json()
        if isinstance(payload, dict) and 'data' in payload:
            return payload.get('data') or {}
        return payload

    def _parse_response_error(self, response):
        """Override of `payment` to extract a usable message from an error response."""
        if self.code != 'ompay':
            return super()._parse_response_error(response)

        try:
            payload = response.json()
        except ValueError:
            return response.text

        error_code = payload.get('error') or ''
        message = payload.get('message') or ''

        # Field-level validation errors carry the detail the merchant needs.
        details = payload.get('details') or []
        if isinstance(details, list):
            fields_msg = '; '.join(
                f"{d.get('field')}: {d.get('message')}"
                for d in details
                if isinstance(d, dict) and d.get('field')
            )
            if fields_msg:
                message = f'{message} ({fields_msg})'.strip()

        if error_code in const.ERROR_MESSAGES:
            message = f'{const.ERROR_MESSAGES[error_code]} {message}'.strip()

        # OMPAY stamps failures with a request id; quoting it turns a support
        # ticket into a one-lookup question.
        if request_id := payload.get('requestId'):
            message = f'{message} [OMPAY request {request_id}]'.strip()

        return message or response.text
