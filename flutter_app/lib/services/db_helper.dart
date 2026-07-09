import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'dart:async';
import '../models.dart';

class DBHelper {
  static final DBHelper instance = DBHelper._init();
  static Database? _database;

  DBHelper._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('expense_iq.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  Future _createDB(Database db, int version) async {
    // 1. Transactions Table
    await db.execute('''
      CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        merchant TEXT,
        payment_mode TEXT,
        bank TEXT,
        date TEXT, -- YYYY-MM-DD
        time TEXT, -- HH:MM
        sms_source TEXT,
        created_at TEXT
      )
    ''');

    // 2. Expense Items Table
    await db.execute('''
      CREATE TABLE expense_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT,
        estimated_price REAL,
        quantity INTEGER DEFAULT 1,
        source TEXT,
        notes TEXT,
        FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
      )
    ''');

    // 3. Budgets Table
    await db.execute('''
      CREATE TABLE budgets (
        category TEXT PRIMARY KEY,
        amount_limit REAL NOT NULL,
        spent_amount REAL DEFAULT 0.0
      )
    ''');

    // Seed default budgets
    final defaultBudgets = {
      "Groceries": 8000.0,
      "Nutrition": 5000.0,
      "Medical": 3000.0,
      "Shopping": 10000.0,
      "Travel": 4000.0,
      "Fuel": 6000.0,
      "Entertainment": 5000.0,
      "Dining": 4000.0,
      "Coffee": 1500.0,
      "Electronics": 15000.0,
      "sent money to friend": 5000.0,
      "sent money to family": 10000.0,
      "Miscellaneous": 3000.0,
    };

    for (var entry in defaultBudgets.entries) {
      await db.insert('budgets', {
        'category': entry.key,
        'amount_limit': entry.value,
        'spent_amount': 0.0,
      });
    }
  }

  // --- TRANSACTION CRUD ---

  Future<int> insertTransaction(TransactionRecord txn, List<ExpenseItem> items) async {
    final db = await instance.database;
    
    return await db.transaction((txnContext) async {
      // 1. Insert Transaction
      final id = await txnContext.insert('transactions', txn.toMap());
      
      // 2. Insert items
      for (var item in items) {
        double itemPrice = item.estimatedPrice;
        if (itemPrice <= 0) {
          itemPrice = txn.amount / items.length;
        }
        await txnContext.insert('expense_items', item.toMap(id));
      }
      
      return id;
    }).then((id) async {
      // Recalculate budgets after successful insert
      await recalculateBudgets();
      return id;
    });
  }

  Future<List<TransactionRecord>> getTransactions() async {
    final db = await instance.database;
    final result = await db.query('transactions', orderBy: 'date DESC, time DESC');
    
    List<TransactionRecord> transactions = [];
    for (var map in result) {
      final txn = TransactionRecord.fromMap(map);
      
      // Fetch items for each transaction
      final itemsMap = await db.query(
        'expense_items', 
        where: 'transaction_id = ?', 
        whereArgs: [txn.id]
      );
      txn.items = itemsMap.map((m) => ExpenseItem.fromMap(m)).toList();
      transactions.add(txn);
    }
    return transactions;
  }

  Future<int> deleteTransaction(int id) async {
    final db = await instance.database;
    final rowsDeleted = await db.delete('transactions', where: 'id = ?', whereArgs: [id]);
    await db.delete('expense_items', where: 'transaction_id = ?', whereArgs: [id]);
    await recalculateBudgets();
    return rowsDeleted;
  }

  // --- BUDGETS CRUD ---

  Future<List<CategoryBudget>> getBudgets() async {
    final db = await instance.database;
    final result = await db.query('budgets');
    return result.map((map) => CategoryBudget.fromMap(map)).toList();
  }

  Future<int> updateBudgetLimit(String category, double limit) async {
    final db = await instance.database;
    return await db.update(
      'budgets',
      {'amount_limit': limit},
      where: 'category = ?',
      whereArgs: [category]
    );
  }

  Future recalculateBudgets() async {
    final db = await instance.database;
    
    // Reset all spent amounts
    await db.update('budgets', {'spent_amount': 0.0});
    
    // Calculate current month's start/end dates
    final now = DateTime.now();
    final startOfMonth = "${now.year}-${now.month.toString().padLeft(2, '0')}-01";
    final endOfMonth = "${now.year}-${now.month.toString().padLeft(2, '0')}-31";

    // Group sum of this month's items
    final List<Map<String, dynamic>> spentSums = await db.rawQuery('''
      SELECT e.category, SUM(e.estimated_price * e.quantity) as spent
      FROM expense_items e
      JOIN transactions t ON e.transaction_id = t.id
      WHERE t.date BETWEEN ? AND ?
      GROUP BY e.category
    ''', [startOfMonth, endOfMonth]);

    for (var row in spentSums) {
      final category = row['category'] as String;
      final spent = (row['spent'] as num?)?.toDouble() ?? 0.0;

      await db.update(
        'budgets',
        {'spent_amount': spent},
        where: 'category = ?',
        whereArgs: [category]
      );
    }
  }

  // --- SEARCH QUERY ---
  Future<List<TransactionRecord>> searchTransactions(String query) async {
    final db = await instance.database;
    
    // Clean string search
    final cleanQuery = "%$query%";
    
    // Perform simple offline matching by Merchant, Category or Item name
    final result = await db.rawQuery('''
      SELECT DISTINCT t.* FROM transactions t
      LEFT JOIN expense_items e ON t.id = e.transaction_id
      WHERE t.merchant LIKE ? OR e.category LIKE ? OR e.item_name LIKE ?
      ORDER BY t.date DESC, t.time DESC
    ''', [cleanQuery, cleanQuery, cleanQuery]);

    List<TransactionRecord> transactions = [];
    for (var map in result) {
      final txn = TransactionRecord.fromMap(map);
      final itemsMap = await db.query('expense_items', where: 'transaction_id = ?', whereArgs: [txn.id]);
      txn.items = itemsMap.map((m) => ExpenseItem.fromMap(m)).toList();
      transactions.add(txn);
    }
    return transactions;
  }
}
