# Changelog

## 19.0.2.0.2

Reliability fixes for payment reconciliation and refunds. No configuration
changes and no new settings.

### Fixed

- **Pending payments could be left unresolved on busy shops.** The scheduled
  action *OMPAY: Poll pending transactions* looked at only the oldest 100 open
  transactions on each run. Checkouts that never reached OMPAY (an on-site card
  form that was opened but never submitted) can never resolve, so enough of them
  could crowd out payments that were genuinely in flight. The action now skips
  transactions that were never sent to OMPAY, checks the newest first, and works
  through the whole backlog in batches of 100.
- **Reversed payments showed as "Unknown payment status".** When OMPAY reports a
  payment as `REVERSED`, an open Odoo transaction is now cancelled with a clear
  message. If the payment was already confirmed in Odoo, it cannot be undone
  automatically, so a note is added to the linked order or invoice asking you to
  review and reconcile it manually.
- **A declined refund showed raw JSON instead of the reason.** The decline
  reason from OMPAY is now shown in the error message.

### Upgrading

Replace the `ompay_tp_plugin` folder, **restart Odoo**, then upgrade the module
(Apps, search for OMPAY, Upgrade) or run:

```
odoo -d <database> -u ompay_tp_plugin --stop-after-init
```

Your API key, secret, checkout flow and PCI acknowledgement are kept. Odoo.sh
projects rebuild automatically when the new commit is deployed.

## 19.0.2.0.1

- Change support address to pgsupport@ompay.com.
