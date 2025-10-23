# TradingView Auto-Login Feature

**Date:** October 20, 2025
**Status:** ✅ IMPLEMENTED

---

## 🎯 What It Does

Automatically logs into TradingView when the bot starts, eliminating the need to manually log in to both browser windows every time you start the bot.

---

## 🚀 Setup

### 1. Add Credentials to .env

Add your TradingView credentials to the `.env` file:

```bash
# TradingView Login Credentials
# Browser 1 (Left window - 5min chart)
TRADINGVIEW_EMAIL_1=your_first_email@example.com
TRADINGVIEW_PASSWORD_1=your_first_password

# Browser 2 (Right window - 15min chart)
TRADINGVIEW_EMAIL_2=your_second_email@example.com
TRADINGVIEW_PASSWORD_2=your_second_password
```

### 2. Use Different Accounts (Recommended)

For best performance, use two different TradingView accounts:
- **Account 1:** For 5-minute chart
- **Account 2:** For 15-minute chart

This prevents any session conflicts.

### 3. Start the Bot

```bash
python3 main.py
```

The bot will automatically:
1. Open browser 1
2. Login to TradingView with credentials 1
3. Navigate to 5-minute chart
4. Open browser 2
5. Login to TradingView with credentials 2
6. Navigate to 15-minute chart

---

## 📊 What You'll See

### With Credentials Configured:

```
🔷 Opening Browser 1 (5-minute chart)...
   🔑 Browser 1: Attempting auto-login...
   📧 Browser 1: Email button clicked
   ✓ Browser 1: Email entered
   ✓ Browser 1: Password entered
   🚀 Browser 1: Login submitted, waiting...
   ✅ Browser 1: Login successful!
   ✅ 5-minute chart loaded with indicator

🔶 Opening Browser 2 (15-minute chart)...
   🔑 Browser 2: Attempting auto-login...
   📧 Browser 2: Email button clicked
   ✓ Browser 2: Email entered
   ✓ Browser 2: Password entered
   🚀 Browser 2: Login submitted, waiting...
   ✅ Browser 2: Login successful!
   ✅ 15-minute chart loaded with indicator

📊 BOTH CHARTS READY!
```

### Without Credentials:

```
🔷 Opening Browser 1 (5-minute chart)...
   ⚠️  Browser 1: No credentials found, skipping auto-login
   💡 Add TRADINGVIEW_EMAIL_1 and TRADINGVIEW_PASSWORD_1 to .env for auto-login
   ✅ 5-minute chart loaded with indicator

🔶 Opening Browser 2 (15-minute chart)...
   ⚠️  Browser 2: No credentials found, skipping auto-login
   💡 Add TRADINGVIEW_EMAIL_2 and TRADINGVIEW_PASSWORD_2 to .env for auto-login
   ✅ 15-minute chart loaded with indicator

📊 BOTH CHARTS READY!

   💡 TIP: Add TradingView credentials to .env for auto-login:
      TRADINGVIEW_EMAIL_1=your_email@example.com
      TRADINGVIEW_PASSWORD_1=your_password
```

---

## 🔍 How It Works

### Auto-Login Process:

1. **Check if Already Logged In**
   - Looks for user menu button
   - If found, skips login

2. **Navigate to Login Page**
   - Goes to `https://www.tradingview.com/accounts/signin/`

3. **Click Email Button**
   - Finds and clicks the "Email" login button
   - CSS selector: `button[name='Email'].emailButton-nKAw8Hvt`

4. **Fill Credentials**
   - Username field: `#id_username`
   - Password field: `#id_password`

5. **Submit Form**
   - Clicks submit button
   - Waits 5 seconds for login to complete

6. **Verify Success**
   - Checks if redirected to chart or main page
   - Reports success or failure

### Code Location:

**File:** `dual_timeframe_bot.py`

**Method:** `auto_login_tradingview()` (lines 277-362)

**Integration:** Called in `setup_browsers()` after each browser is opened (lines 407-414, 440-447)

---

## ⚡ Benefits

1. **Saves Time**
   - No manual login required
   - Both browsers logged in automatically

2. **Faster Bot Startup**
   - Eliminates manual steps
   - Get to trading faster

3. **Consistent Process**
   - Same login flow every time
   - No forgetting to log in

4. **Separate Accounts**
   - Each browser uses its own account
   - No session conflicts

---

## 🛠️ Troubleshooting

### Login Fails

**Issue:** Auto-login reports failure

**Solutions:**
1. Check credentials in `.env` are correct
2. Try logging in manually to verify account works
3. Check for 2FA (not supported by auto-login)
4. Ensure TradingView isn't blocking automated logins

### Already Logged In Message

**Issue:** Bot says "Already logged in!" but you're not logged in

**Solution:**
- This means Chrome profile has saved cookies
- Either correct behavior or false positive
- Check browser manually to verify

### Credentials Not Found

**Issue:** Bot says "No credentials found"

**Solutions:**
1. Check `.env` file has the credentials
2. Ensure no typos in variable names:
   - `TRADINGVIEW_EMAIL_1` (not `TRADINGVIEW_EMAIL1`)
   - `TRADINGVIEW_PASSWORD_1` (not `TRADINGVIEW_PASS_1`)
3. Don't use quotes around values in `.env`

### 2FA Required

**Issue:** TradingView requires 2FA code

**Solution:**
- Auto-login doesn't support 2FA
- Either:
  - Disable 2FA on these accounts
  - Use accounts without 2FA
  - Complete 2FA manually when bot starts

---

## 🔒 Security Notes

### Password Storage:

- Credentials stored in `.env` file (plain text)
- `.env` should be in `.gitignore` (already is)
- **Never commit `.env` to git!**

### Best Practices:

1. **Use Separate Accounts**
   - Create dedicated TradingView accounts for bot
   - Don't use your main account

2. **Free Accounts OK**
   - Bot doesn't need premium features
   - Free accounts work fine

3. **Secure Your Machine**
   - `.env` file is on your local machine
   - Ensure your computer is secure
   - Use strong passwords

4. **No 2FA**
   - Don't enable 2FA on bot accounts
   - Or manually enter 2FA code when bot starts

---

## 📋 Example .env Configuration

```bash
# Hyperliquid Configuration
HYPERLIQUID_PRIVATE_KEY=your_key_here

# Trading Settings
USE_TESTNET=false
AUTO_TRADE=true

# Claude AI Configuration
ANTHROPIC_API_KEY=your_key_here

# Telegram
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# TradingView Login Credentials
# Browser 1 (5-minute chart)
TRADINGVIEW_EMAIL_1=bot_account_1@gmail.com
TRADINGVIEW_PASSWORD_1=SecurePassword123!

# Browser 2 (15-minute chart)
TRADINGVIEW_EMAIL_2=bot_account_2@gmail.com
TRADINGVIEW_PASSWORD_2=AnotherSecurePass456!
```

---

## 🎮 Manual Override

### Want to Login Manually?

Just leave the credentials out of `.env` or use placeholder values:

```bash
TRADINGVIEW_EMAIL_1=your_email_1@example.com
TRADINGVIEW_PASSWORD_1=your_password_1
```

Bot will detect placeholder values and skip auto-login.

---

## 🚀 Quick Start

1. **Get Two TradingView Accounts**
   - Sign up at https://www.tradingview.com
   - Can be free accounts
   - Note down emails and passwords

2. **Add to .env**
   ```bash
   TRADINGVIEW_EMAIL_1=first_account@gmail.com
   TRADINGVIEW_PASSWORD_1=password1
   TRADINGVIEW_EMAIL_2=second_account@gmail.com
   TRADINGVIEW_PASSWORD_2=password2
   ```

3. **Start Bot**
   ```bash
   python3 main.py
   ```

4. **Enjoy Auto-Login!**
   - Bot logs in automatically
   - Both browsers ready in seconds
   - No manual steps needed

---

**Status:** ✅ Ready to use! Add your credentials and enjoy automated login! 🎉
