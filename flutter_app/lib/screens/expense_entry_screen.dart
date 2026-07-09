import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models.dart';
import '../services/db_helper.dart';
import '../services/api_client.dart';

class ExpenseEntryScreen extends StatefulWidget {
  final TransactionRecord? prefilledTxn;
  const ExpenseEntryScreen({super.key, this.prefilledTxn});

  @override
  State<ExpenseEntryScreen> createState() => _ExpenseEntryScreenState();
}

class _ExpenseEntryScreenState extends State<ExpenseEntryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _merchantController = TextEditingController();
  final _amountController = TextEditingController();
  final _bankController = TextEditingController();
  final _dateController = TextEditingController();
  final _itemsController = TextEditingController();
  
  String _paymentMode = 'UPI';
  bool _isSaving = false;
  final APIClient _apiClient = APIClient();

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _dateController.text = DateFormat('yyyy-MM-dd').format(now);
    _bankController.text = 'Cash';

    if (widget.prefilledTxn != null) {
      _merchantController.text = widget.prefilledTxn!.merchant;
      _amountController.text = widget.prefilledTxn!.amount.toString();
      _paymentMode = widget.prefilledTxn!.paymentMode;
      _bankController.text = widget.prefilledTxn!.bank;
      _dateController.text = widget.prefilledTxn!.date;
    }
  }

  String _matchCategory(String text) {
    final lower = text.toLowerCase();
    if (lower.contains('sugar') || lower.contains('salt') || lower.contains('milk') ||
        lower.contains('rice') || lower.contains('tea') || lower.contains('bread') ||
        lower.contains('flour') || lower.contains('atta') || lower.contains('dal') ||
        lower.contains('oil') || lower.contains('paneer') || lower.contains('curd') ||
        lower.contains('vegetable') || lower.contains('fruit') || lower.contains('grocery') ||
        lower.contains('groceries') || lower.contains('dmart') || lower.contains('ration')) {
      return 'Groceries';
    } else if (lower.contains('coffee') || lower.contains('cappuccino') || lower.contains('latte') || lower.contains('starbucks')) {
      return 'Coffee';
    } else if (lower.contains('zomato') || lower.contains('swiggy') || lower.contains('pizza') ||
               lower.contains('burger') || lower.contains('restaurant') || lower.contains('food') ||
               lower.contains('dinner') || lower.contains('lunch') || lower.contains('breakfast')) {
      return 'Food & Dining';
    } else if (lower.contains('uber') || lower.contains('ola') || lower.contains('rapido') ||
               lower.contains('petrol') || lower.contains('fuel') || lower.contains('metro') ||
               lower.contains('cab') || lower.contains('auto')) {
      return 'Transport';
    } else if (lower.contains('phone') || lower.contains('laptop') || lower.contains('electronics') ||
               lower.contains('charger') || lower.contains('earbud') || lower.contains('mobile')) {
      return 'Electronics';
    } else if (lower.contains('friend') || lower.contains('dost')) {
      return 'sent money to friend';
    } else if (lower.contains('family') || lower.contains('mom') || lower.contains('dad')) {
      return 'sent money to family';
    } else if (lower.contains('amazon') || lower.contains('flipkart') || lower.contains('myntra') || lower.contains('cloth')) {
      return 'Shopping';
    } else if (lower.contains('recharge') || lower.contains('bill') || lower.contains('electricity') || lower.contains('wifi')) {
      return 'Utilities';
    }
    return 'Miscellaneous';
  }

  Future<void> _saveExpense() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isSaving = true);
    
    final merchant = _merchantController.text.trim().toUpperCase();
    final amount = double.parse(_amountController.text);
    final bank = _bankController.text.trim();
    final date = _dateController.text.trim();
    final itemsText = _itemsController.text.trim();

    List<ExpenseItem> parsedItems = [];
    
    // Call API categorization
    if (itemsText.isNotEmpty) {
      final aiResult = await _apiClient.categorizeItems(itemsText);
      if (aiResult != null && aiResult['items'] != null) {
        for (var itemMap in aiResult['items']) {
          parsedItems.add(ExpenseItem(
            itemName: itemMap['item_name'] ?? 'Item',
            category: itemMap['category'] ?? 'Miscellaneous',
            subcategory: itemMap['subcategory'] ?? 'General',
            estimatedPrice: (itemMap['estimated_price'] as num?)?.toDouble() ?? (amount / aiResult['items'].length),
            quantity: itemMap['quantity'] ?? 1,
            source: 'SMS',
          ));
        }
      }
    }

    // Instant smart offline fallback if online API wasn't available
    if (parsedItems.isEmpty && itemsText.isNotEmpty) {
      final lines = itemsText.split(RegExp(r'[\n,]')).map((l) => l.trim()).where((l) => l.isNotEmpty).toList();
      final pricePerItem = lines.isNotEmpty ? amount / lines.length : amount;
      for (var line in lines) {
        final cat = _matchCategory(line);
        final capitalized = line[0].toUpperCase() + (line.length > 1 ? line.substring(1) : '');
        parsedItems.add(ExpenseItem(
          itemName: capitalized,
          category: cat,
          subcategory: 'General',
          estimatedPrice: pricePerItem,
          source: widget.prefilledTxn?.smsSource ?? 'Manual',
        ));
      }
    }

    // Fallback if no items entered at all
    if (parsedItems.isEmpty) {
      final cat = _matchCategory(merchant);
      parsedItems.add(ExpenseItem(
        itemName: merchant.isNotEmpty ? merchant : 'General Purchase',
        category: cat,
        subcategory: 'General',
        estimatedPrice: amount,
        source: widget.prefilledTxn?.smsSource ?? 'Manual',
      ));
    }

    final now = DateTime.now();
    final timeStr = DateFormat('HH:mm').format(now);
    final txn = TransactionRecord(
      amount: amount,
      merchant: merchant,
      paymentMode: _paymentMode,
      bank: bank,
      date: date,
      time: timeStr,
      smsSource: widget.prefilledTxn?.smsSource ?? 'Manual',
      createdAt: now.toIso8601String(),
    );

    // Save locally
    await DBHelper.instance.insertTransaction(txn, parsedItems);
    
    // Sync to backend in background
    _apiClient.syncTransaction(txn, parsedItems);

    setState(() => _isSaving = false);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Expense')),
      body: _isSaving
          ? const Center(child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                CircularProgressIndicator(color: AppColors.emerald),
                SizedBox(height: 16),
                Text('AI categorizing purchase items...'),
              ],
            ))
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(16.0),
                children: [
                  TextFormField(
                    controller: _merchantController,
                    decoration: const InputDecoration(labelText: 'Merchant Name', border: OutlineInputBorder()),
                    validator: (v) => v!.isEmpty ? 'Please enter merchant' : null,
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _amountController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Amount (₹)', border: OutlineInputBorder()),
                          validator: (v) => double.tryParse(v!) == null ? 'Invalid amount' : null,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _paymentMode,
                          decoration: const InputDecoration(labelText: 'Payment Mode', border: OutlineInputBorder()),
                          items: ['UPI', 'Card', 'Cash', 'Wallet', 'Bank Transfer']
                              .map((m) => DropdownMenuItem(value: m, child: Text(m)))
                              .toList(),
                          onChanged: (val) => setState(() => _paymentMode = val!),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _bankController,
                          decoration: const InputDecoration(labelText: 'Bank Name', border: OutlineInputBorder()),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: _dateController,
                          decoration: const InputDecoration(labelText: 'Date (YYYY-MM-DD)', border: OutlineInputBorder()),
                          onTap: () async {
                            FocusScope.of(context).requestFocus(FocusNode());
                            DateTime? picked = await showDatePicker(
                              context: context,
                              initialDate: DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2030),
                            );
                            if (picked != null) {
                              _dateController.text = DateFormat('yyyy-MM-dd').format(picked);
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('WHAT DID YOU BUY?', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 12)),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: _itemsController,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      hintText: 'Enter items (one per line, e.g.)\nTea\nSugar\nRice\nSoap',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.emerald,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Save Expense', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    onPressed: _saveExpense,
                  )
                ],
              ),
            ),
    );
  }
}
