import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/db_helper.dart';
import '../models.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  Map<String, double> _categoryTotals = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReportData();
  }

  Future<void> _loadReportData() async {
    setState(() => _isLoading = true);
    final db = DBHelper.instance;
    final txns = await db.getTransactions();

    Map<String, double> tempTotals = {};
    for (var tx in txns) {
      for (var item in tx.items) {
        tempTotals[item.category] = (tempTotals[item.category] ?? 0.0) + (item.estimatedPrice * item.quantity);
      }
    }

    setState(() {
      _categoryTotals = tempTotals;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    List<PieChartSectionData> chartSections = [];
    int colorIdx = 0;
    final List<Color> colors = [Colors.emerald, Colors.blue, Colors.orange, Colors.red, Colors.purple, Colors.teal, Colors.grey];

    _categoryTotals.forEach((category, total) {
      if (total > 0) {
        chartSections.add(PieChartSectionData(
          color: colors[colorIdx % colors.length],
          value: total,
          title: category,
          radius: 60,
          titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
        ));
        colorIdx++;
      }
    });

    return Scaffold(
      appBar: AppBar(title: const Text('Reports & Analytics')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.emerald))
          : _categoryTotals.isEmpty
              ? const Center(child: Text('No spending data to display.'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      const Text('Spending by Category', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 24),
                      SizedBox(
                        height: 220,
                        child: PieChart(
                          PieChartData(
                            sections: chartSections,
                            centerSpaceRadius: 40,
                            sectionsSpace: 2,
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      const Text('Details Table', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey)),
                      const SizedBox(height: 10),
                      ..._categoryTotals.entries.map((e) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8.0),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(e.key, style: const TextStyle(fontWeight: FontWeight.w600)),
                                Text('₹${e.value.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.emerald)),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),
    );
  }
}
