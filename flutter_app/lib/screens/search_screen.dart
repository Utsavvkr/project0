import 'package:flutter/material.dart';
import '../models.dart';
import '../services/db_helper.dart';
import '../services/api_client.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _searchController = TextEditingController();
  List<TransactionRecord> _searchResults = [];
  bool _isLoading = false;
  final APIClient _apiClient = APIClient();

  Future<void> _performSearch() async {
    final query = _searchController.text.trim();
    if (query.isEmpty) return;

    setState(() => _isLoading = true);

    try {
      // 1. Try Online NLP Search
      final apiResults = await _apiClient.searchExpenses(query);
      if (apiResults != null) {
        List<TransactionRecord> tempResults = [];
        for (var map in apiResults) {
          tempResults.add(TransactionRecord.fromMap(map));
        }
        setState(() {
          _searchResults = tempResults;
          _isLoading = false;
        });
        return;
      }
    } catch (_) {
      // Fallback in case of exceptions
    }

    // 2. Offline Database Search fallback
    final localResults = await DBHelper.instance.searchTransactions(query);
    setState(() {
      _searchResults = localResults;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Natural Search')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _searchController,
              decoration: InputDecoration(
                labelText: 'Search e.g. groceries in June',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.search, color: Color(0xFF10B981)),
                  onPressed: _performSearch,
                ),
              ),
              onSubmitted: (_) => _performSearch(),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: Color(0xFF10B981)))
                  : _searchResults.isEmpty
                      ? const Center(child: Text('No matching transactions found.', style: TextStyle(color: Colors.grey)))
                      : ListView.builder(
                          itemCount: _searchResults.length,
                          itemBuilder: (context, index) {
                            final tx = _searchResults[index];
                            return Card(
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              margin: const EdgeInsets.only(bottom: 10),
                              child: ListTile(
                                leading: const CircleAvatar(
                                  backgroundColor: Color(0xFF10B981),
                                  child: Icon(Icons.shopping_bag, color: Colors.white),
                                ),
                                title: Text(tx.merchant, style: const TextStyle(fontWeight: FontWeight.bold)),
                                subtitle: Text('${tx.paymentMode} • ${tx.date}'),
                                trailing: Text('₹${tx.amount.toStringAsFixed(0)}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
