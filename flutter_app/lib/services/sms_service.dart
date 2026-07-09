import 'dart:developer';
import 'package:telephony/telephony.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../models.dart';
import 'db_helper.dart';

// Background message handler must be a top-level function
void onBackgroundMessage(SmsMessage message) {
  log("Background SMS Received: ${message.body}");
  SMSService.instance.processIncomingSMS(message.body ?? '', message.address ?? 'BANK');
}

class SMSService {
  static final SMSService instance = SMSService._init();
  final Telephony telephony = Telephony.instance;
  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

  SMSService._init();

  Future<void> initNotifications() async {
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const InitializationSettings initializationSettings =
        InitializationSettings(android: initializationSettingsAndroid);
        
    await flutterLocalNotificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        // Handle clicking the notification buttons
        if (response.payload != null) {
          // Payloads will contain JSON string of pending transaction
          log("Notification Tapped with payload: ${response.payload}");
        }
      },
    );
  }

  Future<void> requestPermissionsAndStartListening() async {
    final bool? result = await telephony.requestPhoneAndSmsPermissions;
    if (result != null && result) {
      telephony.listenIncomingSms(
        onNewMessage: (SmsMessage message) {
          log("Foreground SMS Received: ${message.body}");
          processIncomingSMS(message.body ?? '', message.address ?? 'BANK');
        },
        onBackgroundMessage: onBackgroundMessage,
      );
    }
  }

  Future<void> processIncomingSMS(String smsText, String sender) async {
    // 1. Regex parsing logic (mirroring backend parser)
    final parsed = parseSMSText(smsText, sender);
    if (parsed == null) return; // Not a transaction SMS

    // 2. Insert transaction in database
    final now = DateTime.now();
    final txn = TransactionRecord(
      amount: parsed['amount'],
      merchant: parsed['merchant'],
      paymentMode: parsed['payment_mode'],
      bank: parsed['bank'],
      date: parsed['date'],
      time: parsed['time'],
      smsSource: sender,
      createdAt: now.toIso8601String(),
    );

    // Initial item is uncategorized
    final defaultItem = ExpenseItem(
      itemName: "Uncategorized Item",
      category: "Miscellaneous",
      subcategory: "General",
      estimatedPrice: parsed['amount'],
      source: "SMS",
    );

    final txnId = await DBHelper.instance.insertTransaction(txn, [defaultItem]);

    // 3. Show Dynamic Alert Notification on Android
    showTransactionNotification(txnId, parsed['amount'], parsed['merchant']);
  }

  Future<void> showTransactionNotification(int txnId, double amount, String merchant) async {
    const AndroidNotificationDetails androidPlatformChannelSpecifics = AndroidNotificationDetails(
      'expense_iq_sms_channel',
      'Transaction Alerts',
      channelDescription: 'Fires when a bank transaction SMS is intercepted',
      importance: Importance.max,
      priority: Priority.high,
      ticker: 'ticker',
      actions: <AndroidNotificationAction>[
        AndroidNotificationAction('add_items', 'Add Items', showsUserInterface: true),
        AndroidNotificationAction('skip', 'Skip', showsUserInterface: false),
      ],
    );

    const NotificationDetails platformChannelSpecifics = NotificationDetails(android: androidPlatformChannelSpecifics);
    
    await flutterLocalNotificationsPlugin.show(
      txnId,
      '₹${amount.toStringAsFixed(0)} spent at $merchant',
      'What did you buy? Tap to categorize your items.',
      platformChannelSpecifics,
      payload: '{"txn_id": $txnId, "amount": $amount, "merchant": "$merchant"}',
    );
  }

  Map<String, dynamic>? parseSMSText(String body, String sender) {
    // Basic verification: does it contain debit keywords?
    final cleanBody = body.toLowerCase();
    if (!cleanBody.contains("debited") && 
        !cleanBody.contains("spent") && 
        !cleanBody.contains("txn of") && 
        !cleanBody.contains("charged")) {
      return null;
    }

    double amount = 0.0;
    String merchant = "Unknown Merchant";
    String paymentMode = "UPI";
    String bank = "Unknown Bank";
    
    // Check bank sender
    final senderUpper = sender.toUpperCase();
    if (senderUpper.contains("SBI")) bank = "SBI";
    else if (senderUpper.contains("HDFC")) bank = "HDFC Bank";
    else if (senderUpper.contains("ICICI")) bank = "ICICI Bank";
    else if (senderUpper.contains("AXIS")) bank = "Axis Bank";
    else if (senderUpper.contains("PAYTM")) bank = "Paytm Bank";

    // Extract amount
    final amtMatch = RegExp(r"(?:rs\.?|inr|amt\.?)\s*([0-9,]+(?:\.[0-9]{2})?)", caseSensitive: false).firstMatch(body);
    if (amtMatch != null) {
      amount = double.tryParse(amtMatch.group(1)!.replaceAll(",", "")) ?? 0.0;
    }

    // Extract merchant
    final merchMatch = RegExp(r"(?:to|at|vpa)\s+([a-zA-Z0-9\s\.\-_@]+?)(?:\s+ref|\s+on|\s+via|\s+ending|\s+\.|\Z)", caseSensitive: false).firstMatch(body);
    if (merchMatch != null) {
      merchant = merchMatch.group(1)!.trim().split("@")[0].toUpperCase();
    }

    // Extract payment mode
    if (cleanBody.contains("upi") || cleanBody.contains("vpa")) {
      paymentMode = "UPI";
    } else if (cleanBody.contains("credit card") || cleanBody.contains("cc")) {
      paymentMode = "Card";
    } else if (cleanBody.contains("debit card") || cleanBody.contains("card ending")) {
      paymentMode = "Card";
    } else if (cleanBody.contains("netbanking") || cleanBody.contains("imps") || cleanBody.contains("neft")) {
      paymentMode = "Bank Transfer";
    }

    final now = DateTime.now();
    final dateStr = "${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}";
    final timeStr = "${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}";

    return {
      'amount': amount,
      'merchant': merchant,
      'payment_mode': paymentMode,
      'bank': bank,
      'date': dateStr,
      'time': timeStr,
    };
  }
}
