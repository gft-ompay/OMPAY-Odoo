# Part of the OMPAY payment provider for Odoo.

import pprint

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class OMPayController(http.Controller):
    _return_url = '/payment/ompay/return'
    _merchant_hosted_url = '/payment/ompay/merchant_hosted'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def ompay_return_from_checkout(self, **data):
        """Process the customer's return from an OMPAY-hosted page.

        OMPAY appends `transaction_id` and `reference_number` to the return URL and
        nothing else. A status sitting in the query string is visible to — and
        forgeable by — the customer, so the query string is used only to identify
        which transaction to ask about. The outcome is always resolved by a
        server-to-server status inquiry.

        :param dict data: The query string parameters appended by OMPAY.
        """
        _logger.info("Handling redirection from OMPAY with data:\n%s", pprint.pformat(data))

        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('ompay', data)
        if not tx_sudo:
            return request.redirect('/payment/status')

        try:
            payment_data = tx_sudo._ompay_fetch_payment_data()
        except ValidationError:
            # Leave the transaction pending; the polling cron will resolve it.
            _logger.warning(
                "Could not confirm OMPAY transaction %s on return.", tx_sudo.reference
            )
            return request.redirect('/payment/status')

        tx_sudo._process('ompay', payment_data)
        return request.redirect('/payment/status')

    @http.route(_merchant_hosted_url, type='jsonrpc', auth='public')
    def ompay_merchant_hosted_payment(self, reference, card, browser=None):
        """Submit a card collected by the inline form to OMPAY.

        :param str reference: The reference of the transaction being paid.
        :param dict card: The card details collected by the inline form.
        :param dict browser: The 3-D Secure 2 browser fingerprint.
        :return: The URL to send the customer to next.
        :rtype: dict
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'ompay', {'reference_number': reference}
        )
        if not tx_sudo:
            raise ValidationError(_("No transaction found matching reference %s.", reference))

        if tx_sudo.provider_id.ompay_flow != 'merchant_hosted':
            raise ValidationError(_("The Merchant Hosted flow is not enabled."))

        # Refuse to charge a transaction that has already moved on, so a replayed
        # request cannot produce a second payment.
        if tx_sudo.state != 'draft':
            raise ValidationError(_("This payment has already been submitted."))

        payment_data = tx_sudo._ompay_create_payment(
            card=self._sanitize_card(card), browser=browser or {}
        )

        # 3-D Secure: the customer finishes on an OMPAY-hosted OTP page.
        if payment_data.get('redirect_url'):
            return {'redirect_url': payment_data['redirect_url']}

        # Frictionless authorisation: confirm before trusting the result.
        try:
            confirmed_data = tx_sudo._ompay_fetch_payment_data()
        except ValidationError:
            return {'redirect_url': '/payment/status'}

        tx_sudo._process('ompay', confirmed_data)
        return {'redirect_url': '/payment/status'}

    @staticmethod
    def _sanitize_card(card):
        """Strip the card payload down to the fields OMPAY expects.

        Anything else the browser sent is dropped rather than forwarded.

        :param dict card: The raw card details from the inline form.
        :return: The sanitized card details.
        :rtype: dict
        """
        card = card or {}
        digits_only = ('number', 'cvv', 'exp_month', 'exp_year')
        sanitized = {}
        for key in ('number', 'exp_month', 'exp_year', 'holder_name', 'cvv'):
            value = str(card.get(key) or '').strip()
            if key in digits_only:
                value = ''.join(c for c in value if c.isdigit())
            if value:
                sanitized[key] = value
        return sanitized
