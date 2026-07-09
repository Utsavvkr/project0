import 'package:flutter/material.dart';

class AppColors {
  static const Color emerald = Color(0xFF10B981);
}

class TransactionRecord {
  int? id;
  final double amount;
  final String merchant;
  final String paymentMode;
  final String bank;
  final String date; // YYYY-MM-DD
  final String time; // HH:MM
  final String smsSource;
  final String createdAt;
  List<ExpenseItem> items;

  TransactionRecord({
    this.id,
    required this.amount,
    required this.merchant,
    required this.paymentMode,
    required this.bank,
    required this.date,
    required this.time,
    required this.smsSource,
    required this.createdAt,
    this.items = const [],
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'amount': amount,
      'merchant': merchant,
      'payment_mode': paymentMode,
      'bank': bank,
      'date': date,
      'time': time,
      'sms_source': smsSource,
      'created_at': createdAt,
    };
  }

  factory TransactionRecord.fromMap(Map<String, dynamic> map) {
    return TransactionRecord(
      id: map['id'],
      amount: map['amount'],
      merchant: map['merchant'] ?? '',
      paymentMode: map['payment_mode'] ?? 'UPI',
      bank: map['bank'] ?? '',
      date: map['date'] ?? '',
      time: map['time'] ?? '',
      smsSource: map['sms_source'] ?? 'Manual',
      createdAt: map['created_at'] ?? '',
    );
  }
}

class ExpenseItem {
  final int? id;
  final int? transactionId;
  final String itemName;
  final String category;
  final String subcategory;
  final double estimatedPrice;
  final int quantity;
  final String source;
  final String notes;

  ExpenseItem({
    this.id,
    this.transactionId,
    required this.itemName,
    required this.category,
    required this.subcategory,
    required this.estimatedPrice,
    this.quantity = 1,
    required this.source,
    this.notes = '',
  });

  Map<String, dynamic> toMap(int txnId) {
    return {
      'id': id,
      'transaction_id': txnId,
      'item_name': itemName,
      'category': category,
      'subcategory': subcategory,
      'estimated_price': estimatedPrice,
      'quantity': quantity,
      'source': source,
      'notes': notes,
    };
  }

  factory ExpenseItem.fromMap(Map<String, dynamic> map) {
    return ExpenseItem(
      id: map['id'],
      transactionId: map['transaction_id'],
      itemName: map['item_name'] ?? '',
      category: map['category'] ?? 'Miscellaneous',
      subcategory: map['subcategory'] ?? 'General',
      estimatedPrice: map['estimated_price'] ?? 0.0,
      quantity: map['quantity'] ?? 1,
      source: map['source'] ?? 'Manual',
      notes: map['notes'] ?? '',
    );
  }
}

class CategoryBudget {
  final String category;
  final double amountLimit;
  final double spentAmount;

  CategoryBudget({
    required this.category,
    required this.amountLimit,
    this.spentAmount = 0.0,
  });

  Map<String, dynamic> toMap() {
    return {
      'category': category,
      'amount_limit': amountLimit,
      'spent_amount': spentAmount,
    };
  }

  factory CategoryBudget.fromMap(Map<String, dynamic> map) {
    return CategoryBudget(
      category: map['category'],
      amountLimit: map['amount_limit'] ?? 0.0,
      spentAmount: map['spent_amount'] ?? 0.0,
    );
  }
}
