import unittest
from reconcile import reconcile, parse, export_csv
class ReconciliationTests(unittest.TestCase):
    def csv(self, rows):
        return 'order_id,amount,currency\n'+rows
    def test_exact_decimal_and_totals(self):
        result=reconcile(self.csv('A,0.10,USD\nB,0.20,USD'),self.csv('A,0.10,USD\nB,0.20,USD'))
        self.assertEqual(result['matched'],2)
        self.assertEqual(result['totals']['USD']['paid'],'0.30')
    def test_all_exception_types(self):
        result=reconcile(self.csv('A,10,USD\nB,20,EUR\nC,30,USD'),self.csv('A,9,USD\nB,20,USD\nD,40,USD'))
        self.assertEqual([r['status'] for r in result['rows']],['amount_mismatch','currency_mismatch','missing_payment','unmatched_payment'])
        self.assertEqual(result['rows'][1]['difference'],'')
        self.assertEqual(result['totals']['EUR']['paid'],'0.00')
        self.assertEqual(result['totals']['USD']['paid'],'69.00')
    def test_duplicate_invalid_and_precision(self):
        for rows in ['A,1,USD\nA,2,USD','A,NaN,USD','A,-1,USD','A,1.001,USD','A,1,U$D']:
            with self.assertRaises(ValueError): parse(self.csv(rows),['order_id','amount','currency'])
    def test_bom_and_formula_safe_export(self):
        result=reconcile('\ufeff'+self.csv('=1+1,10,USD'),self.csv('=1+1,10,USD'))
        self.assertIn("'=1+1",export_csv(result))
    def test_required_header(self):
        with self.assertRaises(ValueError): parse('id,total\nA,10',['order_id','amount','currency'])
if __name__=='__main__': unittest.main()
