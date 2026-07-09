import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models.dart';
import '../services/db_helper.dart';
import 'expense_entry_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  double _monthTotal = 0.0;
  double _weekTotal = 0.0;
  double _todayTotal = 0.0;
  List<TransactionRecord> _recentTransactions = [];
  List<CategoryBudget> _budgets = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    
    final db = DBHelper.instance;
    final txns = await db.getTransactions();
    final budgets = await db.getBudgets();
    
    // Calculate sums
    double mSum = 0;
    double wSum = 0;
    double tSum = 0;
    
    final now = DateTime.now();
    final todayStr = DateFormat('yyyy-MM-dd').format(now);
    final startOfWeek = now.subtract(const Duration(days: 7));
    final startOfMonth = DateTime(now.year, now.month, 1);
    
    for (var tx in txns) {
      final txDate = DateTime.tryParse(tx.date) ?? now;
      if (tx.date == todayStr) {
        tSum += tx.amount;
      }
      if (txDate.isAfter(startOfWeek)) {
        wSum += tx.amount;
      }
      if (txDate.isAfter(startOfMonth)) {
        mSum += tx.amount;
      }
    }

    setState(() {
      _monthTotal = mSum;
      _weekTotal = wSum;
      _todayTotal = tSum;
      _recentTransactions = txns;
      _budgets = budgets;
      _isLoading = false;
    });
  }

  Future<void> _deleteTxn(int id) async {
    await DBHelper.instance.deleteTransaction(id);
    _loadDashboardData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ExpenseIQ', style: TextStyle(fontWeight: FontWeight.bold, fontFamily: 'Outfit')),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDashboardData,
          )
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.emerald))
          : RefreshIndicator(
              onRefresh: _loadDashboardData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Total Monthly Spent Hero Card
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Colors.emerald, Color(0xFF047857)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.emerald.withOpacity(0.3),
                            blurRadius: 10,
                            offset: const Offset(0, 5),
                          )
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'THIS MONTH SPENDING',
                            style: TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '₹${_monthTotal.toStringAsFixed(2)}',
                            style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold, fontFamily: 'Outfit'),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // Today and Week Cards
                    Row(
                      children: [
                        Expanded(
                          child: _buildMetricCard('Today', '₹${_todayTotal.toStringAsFixed(0)}'),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _buildMetricCard('Weekly', '₹${_weekTotal.toStringAsFixed(0)}'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Budgets Section
                    const Text(
                      'BUDGET USAGE',
                      style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                    ..._budgets.where((b) => b.spentAmount > 0).take(3).map((b) => _buildBudgetProgress(b)),
                    if (_budgets.where((b) => b.spentAmount > 0).isEmpty)
                      const Text('No budgets currently active.', style: TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(height: 24),

                    // Recent Transactions
                    const Text(
                      'RECENT TRANSACTIONS',
                      style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                    ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _recentTransactions.length > 5 ? 5 : _recentTransactions.length,
                      itemBuilder: (context, index) {
                        final tx = _recentTransactions[index];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: Colors.emerald.withOpacity(0.1),
                              child: const Icon(Icons.shopping_cart, color: Colors.emerald),
                            ),
                            title: Text(tx.merchant, style: const TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text('${tx.paymentMode} • ${tx.date}'),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text('₹${tx.amount.toStringAsFixed(0)}', style: const TextStyle(fontWeight: FontWeight.bold)),
                                IconButton(
                                  icon: const Icon(Icons.delete, color: Colors.red, size: 18),
                                  onPressed: () => _deleteTxn(tx.id!),
                                )
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: Colors.emerald,
        child: const Icon(Icons.add, color: Colors.white),
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const ExpenseEntryScreen()),
          );
          _loadDashboardData();
        },
      ),
    );
  }

  Widget _buildMetricCard(String label, String value) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, fontFamily: 'Outfit')),
          ],
        ),
      ),
    );
  }

  Widget _buildBudgetProgress(CategoryBudget b) {
    final double pct = b.amountLimit > 0 ? b.spentAmount / b.amountLimit : 0.0;
    Color progressColor = Colors.emerald;
    if (pct >= 1.0) {
      progressColor = Colors.red;
    } else if (pct >= 0.75) {
      progressColor = Colors.amber;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(b.category, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              Text('₹${b.spentAmount.toStringAsFixed(0)} / ₹${b.amountLimit.toStringAsFixed(0)}', style: const TextStyle(fontSize: 12)),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: pct > 1.0 ? 1.0 : pct,
              backgroundColor: Colors.grey[200],
              color: progressColor,
              minHeight: 6,
            ),
          )
        ],
      ),
    );
  }
}
