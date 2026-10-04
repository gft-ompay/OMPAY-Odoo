# Part of the OMPAY payment provider for Odoo.

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_ompay import const


_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return the OMPAY-hosted payment page URL.

        Only the Bank Hosted flow goes through here. Merchant Hosted collects the
        card in an inline form and is started from the controller instead.
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'ompay':
            return res

        payment_data = self._ompay_create_payment()
        redirect_url = payment_data.get('redirect_url')
        if not redirect_url:
            raise ValidationError(_("OMPAY did not return a payment page to redirect to."))

        return {'api_url': redirect_url}

    def _ompay_create_payment(self, card=None, browser=None):
        """Create the transaction at OMPAY and store its identifier.

        Passing `card` selects the Merchant Hosted endpoint; omitting it selects
        Bank Hosted.

        Note: `self.ensure_one()`

        :param dict card: The card details, for the Merchant Hosted flow only.
        :param dict browser: The 3-D Secure 2 browser fingerprint.
        :return: The payment data returned by OMPAY.
        :rtype: dict
        :raise ValidationError: If the request fails.
        """
        self.ensure_one()

        provider = self.provider_id
        currency_code = self.currency_id.name
        base_url = provider.get_base_url()

        payload = {
            'amount': provider._ompay_round_amount(self.amount, currency_code),
            'currency': currency_code,
            # Odoo guarantees a unique reference per transaction, which is what
            # keeps OMPAY from rejecting a retry as a duplicate.
            'reference_number': self.reference,
            'return_url': urls.urljoin(base_url, '/payment/ompay/return'),
        }

        if card:
            endpoint = const.ENDPOINT_MERCHANT_HOSTED
            payload['card'] = card
            payload['browser'] = browser or {}
        else:
            endpoint = const.ENDPOINT_BANK_HOSTED

        # The transaction-level helper passes the reference through and marks the
        # transaction as errored if the request fails, which is what should happen
        # when a payment cannot be started.
        payment_data = self._send_api_request('POST', endpoint, json=payload)

        if transaction_id := payment_data.get('transaction_id'):
            self.provider_reference = transaction_id

        return payment_data

    def _ompay_fetch_payment_data(self):
        """Fetch the authoritative status of this transaction from OMPAY.

        OMPAY sends no webhooks, and the redirect back from the payment page
        carries no status, so this server-to-server lookup is the only trustworthy
        source of an outcome.

        Note: `self.ensure_one()`

        :return: The payment data returned by OMPAY.
        :rtype: dict
        :raise ValidationError: If the request fails.
        """
        self.ensure_one()

        if self.provider_reference:
            payload = {'transaction_id': self.provider_reference}
        else:
            payload = {'reference_number': self.reference}

        # Deliberately the provider-level helper rather than the transaction one:
        # a transient failure to *read* a status must not mark the payment as
        # failed. Callers decide what to do when this raises.
        return self.provider_id._send_api_request(
            'POST', const.ENDPOINT_INQUIRY, json=payload, reference=self.reference
        )

    def _send_refund_request(self):
        """Override of `payment` to send a refund request to OMPAY."""
        if self.provider_code != 'ompay':
            return super()._send_refund_request()

        source_tx = self.source_transaction_id
        if not source_tx.provider_reference:
            raise ValidationError(_("This transaction has no OMPAY reference to refund."))

        provider = self.provider_id
        currency_code = self.currency_id.name

        # The refund transaction carries a negative amount; OMPAY expects a positive one.
        payload = {'amount': provider._ompay_round_amount(abs(self.amount), currency_code)}

        payment_data = self._send_api_request(
            'POST', const.ENDPOINT_REFUND % source_tx.provider_reference, json=payload
        )

        if refund_transaction_id := payment_data.get('refund_transaction_id'):
            self.provider_reference = refund_transaction_id

        refund_status = (payment_data.get('refund_status') or '').upper()
        if payment_data.get('refunded') and refund_status == 'SUCCESSFUL':
            self._set_done()
            remaining = payment_data.get('refundable_remaining')
            if remaining is not None:
                self._log_message_on_linked_documents(_(
                    "OMPAY refund completed. Remaining refundable amount: %s.", remaining
                ))
        else:
            self._set_error(
                payment_data.get('error_message') or _("OMPAY declined the refund.")
            )

    # === BUSINESS METHODS - PAYMENT DATA === #

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'ompay':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('reference_number')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'ompay':
            return super()._extract_amount_data(payment_data)

        amount = payment_data.get('amount')
        currency_code = payment_data.get('currency')
        if amount is None or not currency_code:
            return None  # Skip the amount check rather than fail on a partial payload.

        try:
            # The inquiry endpoint may return the amount as a string.
            amount = float(amount)
        except (TypeError, ValueError):
            return None

        precision_digits = 3 if currency_code.upper() in const.THREE_DECIMAL_CURRENCIES else 2
        return {
            'amount': amount,
            'currency_code': currency_code,
            'precision_digits': precision_digits,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'ompay':
            return super()._apply_updates(payment_data)

        if transaction_id := payment_data.get('transaction_id'):
            self.provider_reference = transaction_id

        status = (payment_data.get('status') or '').upper()
        if not status:
            self._set_error(_("OMPAY returned no payment status."))
        elif status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "OMPAY declined the payment: %s",
                payment_data.get('error_message') or _("no reason given"),
            ))
        else:
            self._set_error(_("Unknown payment status received from OMPAY: %s", status))

    # === BUSINESS METHODS - RECONCILIATION === #

    @api.model
    def _cron_ompay_poll_pending_transactions(self):
        """Resolve OMPAY transactions that never reached a final state.

        Without webhooks, a customer who closes the browser on the OMPAY payment
        page leaves the transaction pending forever. This sweep asks OMPAY for the
        real outcome so a paid order is never left looking unpaid.
        """
        stale_cutoff = fields.Datetime.now() - timedelta(days=7)
        transactions = self.search([
            ('provider_code', '=', 'ompay'),
            ('state', 'in', ['draft', 'pending']),
            ('create_date', '>=', stale_cutoff),
        ], limit=100, order='create_date asc')

        if not transactions:
            return

        _logger.info("Polling %d pending OMPAY transaction(s).", len(transactions))

        for tx in transactions:
            try:
                payment_data = tx._ompay_fetch_payment_data()
            except ValidationError as error:
                _logger.warning(
                    "Could not poll OMPAY transaction %s: %s", tx.reference, error
                )
                continue

            status = (payment_data.get('status') or '').upper()
            if status in const.PAYMENT_STATUS_MAPPING['pending']:
                continue  # Genuinely still in flight; leave it alone.

            tx._process('ompay', payment_data)
            self.env.cr.commit()  # Keep a slow provider from losing resolved transactions.
