"""Decimal-based reconciliation of merchant orders and settlement exports."""
import csv
import io
from decimal import Decimal, InvalidOperation

LIMIT = 5000

def parse(text, columns):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not reader.fieldnames or not set(columns).issubset(reader.fieldnames):
        raise ValueError('Required columns: ' + ', '.join(columns))
    result = {}
    for line, row in enumerate(reader, 2):
        if line > LIMIT + 1:
            raise ValueError(f'Maximum {LIMIT} rows per file')
        key = (row.get('order_id') or '').strip()
        currency = (row.get('currency') or '').strip().upper()
        if not key or len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise ValueError(f'Row {line}: order_id and three-letter currency required')
        if key in result:
            raise ValueError(f'Row {line}: duplicate order_id {key}')
        try:
            amount = Decimal(row['amount'])
        except (InvalidOperation, TypeError):
            raise ValueError(f'Row {line}: invalid amount') from None
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            raise ValueError(f'Row {line}: amount must be non-negative with up to two decimal places')
        result[key] = {'amount': amount, 'currency': currency}
    return result

def reconcile(orders_text, payments_text):
    orders = parse(orders_text, ['order_id', 'amount', 'currency'])
    payments = parse(payments_text, ['order_id', 'amount', 'currency'])
    rows = []
    totals = {}
    for key in sorted(orders.keys() | payments.keys()):
        order, payment = orders.get(key), payments.get(key)
        if order is None:
            status, action = 'unmatched_payment', 'Locate order or investigate payment reference'
        elif payment is None:
            status, action = 'missing_payment', 'Check settlement date and payment provider'
        elif order['currency'] != payment['currency']:
            status, action = 'currency_mismatch', 'Verify currencies; no automatic FX conversion'
        elif order['amount'] != payment['amount']:
            status, action = 'amount_mismatch', 'Check fees, refunds and partial settlement'
        else:
            status, action = 'matched', 'No discrepancy detected'
        currency = order['currency'] if order else payment['currency']
        bucket = totals.setdefault(currency, {'ordered': Decimal(0), 'paid': Decimal(0)})
        if order:
            bucket['ordered'] += order['amount']
        if payment:
            totals.setdefault(payment['currency'], {'ordered': Decimal(0), 'paid': Decimal(0)})['paid'] += payment['amount']
        delta = payment['amount'] - order['amount'] if order and payment and order['currency'] == payment['currency'] else None
        rows.append({'order_id': key, 'currency': currency, 'order_amount': str(order['amount']) if order else '',
                     'payment_currency': payment['currency'] if payment else '', 'paid_amount': str(payment['amount']) if payment else '',
                     'difference': f'{delta:.2f}' if delta is not None else '', 'status': status, 'next_action': action})
    return {'rows': rows, 'matched': sum(r['status'] == 'matched' for r in rows),
            'exceptions': sum(r['status'] != 'matched' for r in rows),
            'totals': {c: {k: f'{v:.2f}' for k, v in vals.items()} for c, vals in sorted(totals.items())}}

def export_csv(result):
    stream = io.StringIO(newline='')
    fields = ['order_id', 'currency', 'order_amount', 'payment_currency', 'paid_amount', 'difference', 'status', 'next_action']
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in result['rows']:
        # Neutralize spreadsheet formulas in untrusted identifiers.
        writer.writerow({k: "'" + v if v.startswith(('=', '+', '-', '@', '\t', '\r')) and k == 'order_id' else v for k, v in row.items()})
    return stream.getvalue()
