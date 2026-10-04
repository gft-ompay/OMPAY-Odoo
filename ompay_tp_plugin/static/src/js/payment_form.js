/**
 * OMPAY payment form handling.
 *
 * Bank Hosted needs nothing here: Odoo's default redirect flow submits the form
 * built by the `redirect_form` template. Merchant Hosted collects the card in the
 * inline form and hands it to the server, which calls the OMPAY API.
 */

import { patch } from '@web/core/utils/patch';
import { rpc, RPCError } from '@web/core/network/rpc';
import { _t } from '@web/core/l10n/translation';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    // #=== DOM MANIPULATION ===#

    /**
     * Switch to the direct flow when OMPAY is configured for Merchant Hosted.
     *
     * The inline form is only rendered for Merchant Hosted, so its presence is
     * what distinguishes the two flows on the client.
     *
     * @override method from @payment/interactions/payment_form
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'ompay') {
            await super._prepareInlineForm(...arguments);
            return;
        }
        if (flow === 'token') {
            return;
        }

        const inlineForm = document.getElementById(`o_ompay_inline_form_${providerId}`);
        if (!inlineForm) {
            return;  // Bank Hosted: let Odoo run its standard redirect flow.
        }

        this._ompayBindInputFormatting(providerId);
        this._setPaymentFlow('direct');
    },

    /**
     * Format the card number and expiry as the customer types.
     *
     * @param {number} providerId - The id of the selected payment option's provider.
     * @return {void}
     */
    _ompayBindInputFormatting(providerId) {
        const numberInput = document.getElementById(`o_ompay_card_number_${providerId}`);
        const expiryInput = document.getElementById(`o_ompay_card_expiry_${providerId}`);
        const cvvInput = document.getElementById(`o_ompay_card_cvv_${providerId}`);

        if (numberInput && !numberInput.dataset.ompayBound) {
            numberInput.dataset.ompayBound = '1';
            numberInput.addEventListener('input', () => {
                const digits = numberInput.value.replace(/\D/g, '').slice(0, 19);
                numberInput.value = digits.replace(/(.{4})/g, '$1 ').trim();
            });
        }

        if (expiryInput && !expiryInput.dataset.ompayBound) {
            expiryInput.dataset.ompayBound = '1';
            expiryInput.addEventListener('input', () => {
                const digits = expiryInput.value.replace(/\D/g, '').slice(0, 4);
                expiryInput.value = digits.length < 3
                    ? digits
                    : `${digits.slice(0, 2)} / ${digits.slice(2)}`;
            });
        }

        if (cvvInput && !cvvInput.dataset.ompayBound) {
            cvvInput.dataset.ompayBound = '1';
            cvvInput.addEventListener('input', () => {
                cvvInput.value = cvvInput.value.replace(/\D/g, '').slice(0, 4);
            });
        }
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Send the collected card to the server, then follow OMPAY's instruction.
     *
     * OMPAY answers with an OTP page to visit when 3-D Secure is required, and
     * otherwise the server confirms the outcome before replying.
     *
     * @override method from @payment/interactions/payment_form
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'ompay') {
            await super._processDirectFlow(...arguments);
            return;
        }

        const providerId = processingValues.provider_id;
        const card = this._ompayCollectCard(providerId);
        if (!card) {
            this._displayErrorDialog(
                _t("Incomplete card details"),
                _t("Please enter your full card number, expiry date and security code."),
            );
            this._enableButton();
            return;
        }

        try {
            const { redirect_url } = await rpc('/payment/ompay/merchant_hosted', {
                reference: processingValues.reference,
                card: card,
                browser: this._ompayCollectBrowserData(),
            });
            window.location = redirect_url;
        } catch (error) {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton();
            } else {
                throw error;
            }
        }
    },

    /**
     * Read and validate the card fields.
     *
     * @param {number} providerId - The id of the selected payment option's provider.
     * @return {object|null} The card details, or null when they are incomplete.
     */
    _ompayCollectCard(providerId) {
        const value = id => (document.getElementById(id)?.value || '').trim();

        const number = value(`o_ompay_card_number_${providerId}`).replace(/\D/g, '');
        const expiry = value(`o_ompay_card_expiry_${providerId}`).replace(/\D/g, '');
        const cvv = value(`o_ompay_card_cvv_${providerId}`).replace(/\D/g, '');
        const holderName = value(`o_ompay_card_holder_${providerId}`);

        if (number.length < 12 || number.length > 19 || expiry.length < 4 || cvv.length < 3) {
            return null;
        }

        return {
            number: number,
            exp_month: expiry.slice(0, 2),
            exp_year: `20${expiry.slice(2, 4)}`,
            cvv: cvv,
            holder_name: holderName,
        };
    },

    /**
     * Collect the browser characteristics 3-D Secure 2 requires.
     *
     * @return {object} The browser fingerprint.
     */
    _ompayCollectBrowserData() {
        return {
            userAgent: navigator.userAgent,
            acceptHeader: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            language: navigator.language || 'en-US',
            colorDepth: String(window.screen?.colorDepth || 24),
            screenWidth: String(window.screen?.width || 1920),
            screenHeight: String(window.screen?.height || 1080),
            tz: String(new Date().getTimezoneOffset()),
            javaEnabled: false,
            javascriptEnabled: true,
        };
    },

});
