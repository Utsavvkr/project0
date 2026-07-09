import 'dart:convert';
import 'dart:developer';
import 'package:http/http.dart' as http;
import '../models.dart';

class APIClient {
  static const String baseUrl = "http://10.0.2.2:8000/api"; // 10.0.2.2 is local host on Android emulator
  
  // Categorize raw text of items using AI
  Future<Map<String, dynamic>?> categorizeItems(String itemsText) async {
    final url = Uri.parse("$baseUrl/categorize");
    try {
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"items_text": itemsText}),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        log("API Categorization failed with status: ${response.statusCode}");
      }
    } catch (e) {
      log("API Client exception in categorizeItems: $e");
    }
    return null;
  }

  // Get AI insights
  Future<Map<String, dynamic>?> getInsights() async {
    final url = Uri.parse("$baseUrl/insights");
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      log("API Client exception in getInsights: $e");
    }
    return null;
  }

  // Natural Language Search
  Future<List<Map<String, dynamic>>?> searchExpenses(String query) async {
    final url = Uri.parse("$baseUrl/search?q=${Uri.encodeComponent(query)}");
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.cast<Map<String, dynamic>>();
      }
    } catch (e) {
      log("API Client exception in searchExpenses: $e");
    }
    return null;
  }

  // Sync a transaction to the backend
  Future<bool> syncTransaction(TransactionRecord txn, List<ExpenseItem> items) async {
    final url = Uri.parse("$baseUrl/transactions");
    
    final payload = {
      "amount": txn.amount,
      "merchant": txn.merchant,
      "payment_mode": txn.paymentMode,
      "bank": txn.bank,
      "date": txn.date,
      "time": txn.time,
      "sms_source": txn.smsSource,
      "items": items.map((item) => {
        "item_name": item.itemName,
        "category": item.category,
        "subcategory": item.subcategory,
        "estimated_price": item.estimatedPrice,
        "quantity": item.quantity,
        "notes": item.notes
      }).toList()
    };

    try {
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(payload),
      );
      return response.statusCode == 200;
    } catch (e) {
      log("API Client sync exception: $e");
      return false;
    }
  }
}
