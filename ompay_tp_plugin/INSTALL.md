# OMPAY Payment Gateway — Installation

Accept card payments in Odoo 19 through OMPAY.

## Before you start

You need:

- **Odoo 19.0**, self-hosted or on Odoo.sh.
  Odoo Online (SaaS) cannot install this module — Odoo does not permit
  third-party modules containing Python code on their hosted platform.
- An **OMPAY merchant account** with your API Key and API Secret.
- Access to your Odoo server's **addons directory**.

## 1. Install the module

**Self-hosted**

1. Extract this archive so the `ompay_tp_plugin` folder sits inside your addons
   path, for example `/opt/odoo/addons/ompay_tp_plugin`.
2. Restart the Odoo service.
3. In Odoo, enable Developer Mode (Settings → General Settings → Developer
   Tools), then go to **Apps** and click **Update Apps List**.
4. Search for **OMPAY**, and click **Install**.

**Odoo.sh**

1. Add the `ompay_tp_plugin` folder to your project's Git repository.
2. Commit and push. Odoo.sh rebuilds automatically.
3. Go to **Apps**, search for **OMPAY**, and click **Install**.

## 2. Enter your credentials

Go to **Accounting › Configuration › Payment Providers** and open **OMPAY**.

| Field | What to enter |
|---|---|
| API Key | The key OMPAY issued you |
| API Secret | The secret OMPAY issued you |
| Checkout Flow | **Bank Hosted** (recommended) |

Leave the provider in **Test Mode** for now. Test Mode uses the OMPAY sandbox;
**Enabled** uses the live API. Sandbox and production use different credentials,
so make sure the pair you paste matches the mode you are in.

Then set **Published** so the provider appears at checkout.

## 3. Check your currency

OMPAY settles in Omani Rial, which uses **three decimal places**.

Go to **Accounting › Configuration › Currencies**, open **OMR**, and confirm
Rounding is `0.001` and Decimal Places is `3`. If it is set to 2, every amount
will round differently from what OMPAY charges.

## 4. Test before going live

With sandbox credentials and the provider in Test Mode:

1. Create a customer invoice and send yourself the payment link.
2. Pay an amount that does **not** end in `00` — for example `15.750`. It should
   succeed.
3. Pay an amount ending in `00` — for example `10.000`. The sandbox declines
   these on purpose, so you can confirm failures are handled.
4. Start a payment and close the browser on the OMPAY page. The order stays
   pending until the scheduled action **OMPAY: Poll pending transactions**
   resolves it. You can run it manually from
   Settings → Technical → Scheduled Actions.

## 5. Go live

1. Replace the sandbox API Key and Secret with your production pair.
2. Set the provider state to **Enabled**.
3. Make one small real payment and refund it to confirm the round trip.

## About the two checkout flows

**Bank Hosted** sends the customer to a secure OMPAY page to enter their card.
Card data never reaches your server, which keeps you in the lightest PCI DSS
scope (SAQ A). This is the right choice for almost every merchant.

**Merchant Hosted** renders the card form on your own checkout and sends the
card number through your server. This places your business in **PCI DSS SAQ D**,
the heaviest compliance tier. The module will not run this flow until you tick
the PCI acknowledgement in the provider settings. Do not enable it unless your
business has completed SAQ D certification.

Each flow is a separate capability on your OMPAY account. If a payment is
rejected with a `402` error, the flow is not enabled for you — contact OMPAY.

## Troubleshooting

| Symptom | Cause |
|---|---|
| OMPAY missing at checkout | Provider not Published, credentials blank, or Merchant Hosted selected without the PCI acknowledgement |
| "OMPAY rejected the API key or secret" | Credentials do not match the mode — sandbox keys in Test Mode, production keys when Enabled |
| `402` on payment | The flow or the card's BIN range is not enabled on your OMPAY account |
| Order stuck pending | Run the **OMPAY: Poll pending transactions** scheduled action |

## Support

support@ompay.com · https://ompay.om
