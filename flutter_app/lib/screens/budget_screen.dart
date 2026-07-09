import 'package:flutter/material.dart';
import '../models.dart';
import '../services/db_helper.dart';

class BudgetScreen extends StatefulWidget {
  const BudgetScreen({super.key});

  @override
  State<BudgetScreen> createState() => _BudgetScreenState();
}

class _BudgetScreenState extends State<BudgetScreen> {
  List<CategoryBudget> _budgets = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadBudgets();
  }

  Future<void> _loadBudgets() async {
    setState(() => _isLoading = true);
    final budgets = await DBHelper.instance.getBudgets();
    setState(() {
      _budgets = budgets;
      _isLoading = false;
    });
  }

  Future<void> _editLimit(CategoryBudget b) async {
    final controller = TextEditingController(text: b.amountLimit.toString());
    
    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Edit ${b.category} Budget'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Limit (₹)'),
        ),
        actions: [
          TextButton(
            child: const Text('Cancel'),
            onPressed: () => Navigator.pop(context),
          ),
          TextButton(
            child: const Text('Save'),
            onPressed: () async {
              final newLimit = double.tryParse(controller.text) ?? b.amountLimit;
              await DBHelper.instance.updateBudgetLimit(b.category, newLimit);
              Navigator.pop(context);
              _loadBudgets();
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Category Budgets')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.emerald))
          : ListView.builder(
              padding: const EdgeInsets.all(16.0),
              itemCount: _budgets.length,
              itemBuilder: (context, index) {
                final b = _budgets[index];
                final pct = b.amountLimit > 0 ? b.spentAmount / b.amountLimit : 0.0;
                Color statusColor = Colors.emerald;
                if (pct >= 1.0) statusColor = Colors.red;
                else if (pct >= 0.75) statusColor = Colors.amber;

                return Card(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(b.category, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                            IconButton(
                              icon: const Icon(Icons.edit, size: 18, color: Colors.emerald),
                              onPressed: () => _editLimit(b),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('Spent: ₹${b.spentAmount.toStringAsFixed(0)}', style: TextStyle(color: statusColor, fontWeight: FontWeight.bold)),
                            Text('Limit: ₹${b.amountLimit.toStringAsFixed(0)}', style: const TextStyle(color: Colors.grey)),
                          ],
                        ),
                        const SizedBox(height: 10),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: pct > 1.0 ? 1.0 : pct,
                            color: statusColor,
                            backgroundColor: Colors.grey[200],
                            minHeight: 8,
                          ),
                        )
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
