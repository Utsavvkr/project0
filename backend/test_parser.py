import unittest
from app.sms_parser import parse_sms
from app.ai_service import local_categorize_item, local_nlp_search

class TestExpenseIQEngine(unittest.TestCase):

    def test_sms_parsing(self):
        # 1. Standard UPI SMS
        sms1 = "Rs. 850 debited via UPI to DMART"
        res1 = parse_sms(sms1)
        self.assertEqual(res1['amount'], 850.0)
        self.assertEqual(res1['merchant'], 'DMART')
        self.assertEqual(res1['payment_mode'], 'UPI')

        # 2. Card SMS
        sms2 = "Txn of Rs. 150.00 on Credit Card XX7890 at STARBUCKS on 09/07/26 14:30."
        res2 = parse_sms(sms2)
        self.assertEqual(res2['amount'], 150.0)
        self.assertEqual(res2['merchant'], 'STARBUCKS')
        self.assertEqual(res2['payment_mode'], 'Card')

        # 3. Complex Bank body
        sms3 = "Alert: Rs.450.00 debited from SBI Account ...4321 via UPI to SWIGGY Ref 12345"
        res3 = parse_sms(sms3)
        self.assertEqual(res3['amount'], 450.0)
        self.assertEqual(res3['merchant'], 'SWIGGY')
        self.assertEqual(res3['payment_mode'], 'UPI')
        self.assertEqual(res3['bank'], 'SBI')
        self.assertEqual(res3['transaction_id'], '12345')

    def test_local_categorization(self):
        # 1. Nutrition item
        res1 = local_categorize_item("Protein Powder")
        self.assertEqual(res1['category'], 'Nutrition')

        # 2. Coffee item
        res2 = local_categorize_item("cappuccino x2 Rs. 240")
        self.assertEqual(res2['category'], 'Coffee')
        self.assertEqual(res2['estimated_price'], 240.0)
        self.assertEqual(res2['item_name'], 'Cappuccino')

        # 3. Medical item
        res3 = local_categorize_item("Paracetamol tablets")
        self.assertEqual(res3['category'], 'Medical')

    def test_local_nlp_search(self):
        # 1. Grocery in June
        res1 = local_nlp_search("show grocery expenses from June")
        self.assertEqual(res1.get('category'), 'Groceries')
        self.assertEqual(res1.get('month'), 6)

        # 2. Amazon limit
        res2 = local_nlp_search("How much did I spend on Amazon above 500?")
        self.assertEqual(res2.get('merchant'), 'AMAZON')
        self.assertEqual(res2.get('min_amount'), 500.0)

if __name__ == '__main__':
    unittest.main()
