# OMPAY Odoo modules

Odoo integrations for the [OMPAY](https://ompay.om) payment gateway.

Each branch targets one Odoo series, which is the layout the
[Odoo Apps Store](https://apps.odoo.com) expects.

| Branch | Odoo | Modules |
|--------|------|---------|
| `19.0` | 19.0 | `ompay_tp_plugin` |

## ompay_tp_plugin

Accept card payments in Omani Rial through OMPAY, using either the Bank Hosted
redirect or the Merchant Hosted on-site card form.

- **Bank Hosted** — the customer pays on a secure OMPAY page, so card data never
  touches the merchant server (PCI DSS SAQ A). Recommended.
- **Merchant Hosted** — the card form is rendered on the merchant's checkout and
  the card is posted to OMPAY from their server (PCI DSS SAQ D). Disabled until
  the merchant confirms compliance in the provider settings.

Supports 3-D Secure 2, full and partial refunds, and a scheduled reconciliation
sweep that resolves payments abandoned mid-checkout. OMPAY sends no webhooks, so
every outcome is confirmed by a server-to-server status inquiry.

### Requirements

- Odoo 19.0 (Community or Enterprise)
- An OMPAY merchant account with API credentials
- The checkout flow you intend to use enabled on your OMPAY account
- Self-hosted or Odoo.sh — Odoo Online does not permit third-party modules
  containing Python code

### Installation

Copy `ompay_tp_plugin` into your addons path, update the apps list, and install
it. Then open **Accounting › Configuration › Payment Providers › OMPAY** and
enter the API Key and API Secret issued to you.

Leave the provider in **Test Mode** to use the OMPAY sandbox; setting it to
**Enabled** switches to the live API, so make sure the credentials match.

If your store prices in Omani Rial, check that the OMR currency is set to
**3 decimal places** — OMR is a three-decimal currency and the wrong precision
will round against what OMPAY settles.

### Support

pgsupport@ompay.com · [ompay.om](https://ompay.om)

### Licence

LGPL-3. See [LICENSE](ompay_tp_plugin/LICENSE).
