# 🏆 Iran Tournament Backend - Clash Royale Tournament Platform

پلتفرم جامع مدیریت تورنمنت‌های Clash Royale برای کاربران ایرانی با قابلیت ردیابی خودکار بازی‌ها، رتبه‌بندی real-time و سیستم پرداخت آنلاین.

![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Redis](https://img.shields.io/badge/Redis-7-red.svg)
![Celery](https://img.shields.io/badge/Celery-5.3-green.svg)

---

## 📋 فهرست مطالب

- [ویژگی‌های اصلی](#ویژگی-های-اصلی)
- [Technology Stack](#technology-stack)
- [فلوی کامل پروژه](#فلوی-کامل-پروژه)
- [ساختار پروژه](#ساختار-پروژه)
- [نصب و راه‌اندازی](#نصب-و-راه-اندازی)
- [تنظیمات Clash Royale API](#تنظیمات-clash-royale-api)
- [مدل‌های دیتابیس](#مدل-های-دیتابیس)
- [API Endpoints](#api-endpoints)
- [Celery Tasks](#celery-tasks)
- [Admin Panel](#admin-panel)
- [نمونه استفاده](#نمونه-استفاده)
- [Deployment](#deployment)

---

## 🎯 ویژگی‌های اصلی

### 🎮 مدیریت تورنمنت‌ها
- ✅ ساخت و مدیریت تورنمنت‌های Clash Royale
- ✅ حالت‌های مختلف بازی (Normal, Double Elixir, Triple Elixir, Draft و...)
- ✅ سیستم ثبت‌نام با پرداخت آنلاین (ZarinPal, IDPay, NextPay, Zibal)
- ✅ مدیریت جوایز و توزیع خودکار
- ✅ سیستم دعوت‌نامه برای تورنمنت‌های خصوصی

### 🔗 اتصال به Clash Royale API
- ✅ **ردیابی خودکار بازی‌ها** - هر 2 دقیقه battle logs رو sync می‌کنه
- ✅ ذخیره کامل اطلاعات هر بازی (تاج‌ها، HP برج‌ها، کارت‌های استفاده شده)
- ✅ **Leaderboard Real-time** - رتبه‌بندی لحظه‌ای بر اساس نتایج بازی‌ها
- ✅ فیلتر خودکار بازی‌های داخل تایم تورنمنت
- ✅ Cache برای بهینه‌سازی درخواست‌ها

### 📧 سیستم اعلان‌ها
- ✅ ارسال خودکار Email/SMS بعد از شروع تورنمنت
- ✅ اطلاع‌رسانی تگ و رمز تورنمنت به شرکت‌کنندگان
- ✅ یادآوری زمان مسابقات
- ✅ اعلان‌های درون‌برنامه‌ای
- ✅ تنظیمات شخصی‌سازی اعلان‌ها

### 💰 سیستم مالی
- ✅ کیف پول کاربران
- ✅ پرداخت آنلاین با درگاه‌های ایرانی
- ✅ واریز و برداشت وجه
- ✅ سیستم کوپن تخفیف
- ✅ تراکنش‌های مالی با احراز هویت
- ✅ مدیریت کمیسیون پلتفرم

### 👥 مدیریت کاربران
- ✅ احراز هویت با OTP (کد یکبار مصرف) و JWT Token
- ✅ لاگین/رجیستر فقط با شماره موبایل
- ✅ تأیید خودکار شماره موبایل با OTP
- ✅ پروفایل کاربری با تگ Clash Royale
- ✅ آمار و رتبه‌بندی کاربران
- ✅ تاریخچه تورنمنت‌ها و مسابقات

### 🏅 سیستم مسابقات
- ✅ مدیریت مسابقات درون تورنمنت
- ✅ ثبت نتایج توسط بازیکنان
- ✅ تایید نتایج توسط ادمین
- ✅ فرمت Best of 3/5/7
- ✅ نمایش آمار دقیق هر مسابقه

### 💬 سیستم چت تورنمنت
- ✅ چت گروهی بین شرکت‌کنندگان تورنمنت
- ✅ قابلیت پاسخ به پیام‌ها (Reply)
- ✅ حذف نرم (Soft delete) برای مدیریت پیام‌ها
- ✅ دسترسی فقط برای شرکت‌کنندگان تایید شده

---

## 🛠 Technology Stack

### Backend
- **Framework**: Django 4.2
- **API**: Django REST Framework
- **Authentication**: JWT (Simple JWT)
- **Task Queue**: Celery 5.3
- **Message Broker**: Redis
- **Database**: PostgreSQL 15 (Production) / SQLite (Development)

### Third-Party APIs
- **Clash Royale Official API**: برای دریافت battle logs و اطلاعات بازیکنان
- **Payment Gateways**: ZarinPal, IDPay, NextPay, Zibal
- **SMS Providers**: Kavenegar, Ghasedak

### Tools & Libraries
- **CORS Handling**: django-cors-headers
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Rich Text Editor**: django-ckeditor
- **Filtering**: django-filter
- **Cache**: django-redis

---

## 🔄 فلوی کامل پروژه

این بخش فرآیند کامل یک تورنمنت را از ساخت تا واریز جوایز شرح می‌دهد:

### 1️⃣ ساخت تورنمنت (توسط ادمین)

```
ادمین وارد پنل ادمین می‌شود
    ↓
تورنمنت جدید ایجاد می‌کند و اطلاعات زیر را وارد می‌کند:
  • عنوان و توضیحات
  • تاریخ شروع/پایان ثبت‌نام
  • تاریخ شروع/پایان تورنمنت
  • هزینه ورودی و حداکثر شرکت‌کنندگان
  • تنظیمات بازی (game mode, level cap, max losses)
  • کمیسیون پلتفرم (%)
    ↓
تورنمنت در وضعیت "draft" ذخیره می‌شود
    ↓
ادمین تورنمنت را به Clash Royale می‌رود و یک تورنمنت می‌سازد
    ↓
تگ (#ABC123) و رمز تورنمنت را در پنل ادمین وارد می‌کند
    ↓
گزینه "auto_tracking_enabled" را فعال می‌کند
    ↓
وضعیت تورنمنت را به "registration" تغییر می‌دهد
```

### 2️⃣ ثبت‌نام کاربران

```
کاربر لیست تورنمنت‌های فعال را مشاهده می‌کند
    ↓
روی تورنمنت کلیک می‌کند و جزئیات را می‌بیند
    ↓
دکمه "ثبت‌نام" را می‌زند
    ↓
سیستم چک می‌کند:
  • آیا تورنمنت فعال است؟
  • آیا ظرفیت باقی مانده؟
  • آیا کاربر قبلاً ثبت‌نام کرده؟
    ↓
کاربر به درگاه پرداخت هدایت می‌شود
    ↓
پرداخت انجام می‌شود (ZarinPal/IDPay/NextPay/Zibal)
    ↓
وضعیت TournamentParticipant به "confirmed" تغییر می‌کند
    ↓
هزینه ورودی به prize_pool تورنمنت اضافه می‌شود
    ↓
نوتیفیکیشن تایید ثبت‌نام ارسال می‌شود
```

### 3️⃣ شروع تورنمنت

```
زمان شروع تورنمنت فرا می‌رسد
    ↓
Celery task "check_tournament_start_times" هر 1 دقیقه چک می‌کند
    ↓
تورنمنت‌هایی که باید شروع شوند پیدا می‌شوند
    ↓
برای هر تورنمنت:
  1. وضعیت به "ongoing" تغییر می‌کند
  2. tracking_started_at = زمان فعلی
  3. Task "send_tournament_start_notifications" اجرا می‌شود
    ↓
به تمام شرکت‌کنندگان Email/SMS ارسال می‌شود:
  📧 "تورنمنت شما شروع شد!"
  📱 "تگ: #ABC123"
  🔑 "رمز: password123"
  🎮 "به کلش رویال بروید و شروع کنید"
```

### 4️⃣ ردیابی خودکار بازی‌ها

```
تورنمنت در وضعیت "ongoing" است
auto_tracking_enabled = True
    ↓
Celery task "sync_tournament_battle_logs" هر 2 دقیقه اجرا می‌شود
    ↓
برای هر تورنمنت فعال:
  1. لیست شرکت‌کنندگان را می‌گیرد
  2. برای هر شرکت‌کننده:
     • با Clash Royale API تماس می‌گیرد
     • 25 بازی اخیر را دریافت می‌کند
     • بازی‌هایی که بعد از tracking_started_at هستند فیلتر می‌شوند
     • بازی‌های جدید در PlayerBattleLog ذخیره می‌شوند
    ↓
برای هر بازی جدید، اطلاعات زیر ذخیره می‌شود:
  • player_tag, opponent_tag
  • player_crowns, opponent_crowns
  • is_winner, is_draw
  • battle_time
  • player_cards, opponent_cards
  • arena_name, game_mode
    ↓
Task "calculate_tournament_rankings" برای آپدیت رتبه‌بندی اجرا می‌شود
```

### 5️⃣ محاسبه رتبه‌بندی Real-time

```
هر بار که بازی‌های جدید sync می‌شوند
    ↓
برای هر شرکت‌کننده TournamentRanking آپدیت می‌شود:
    ↓
آمار محاسبه می‌شود:
  • total_battles = تعداد کل بازی‌ها
  • total_wins = تعداد بردها
  • total_losses = تعداد باخت‌ها
  • total_draws = تعداد مساوی‌ها
  • total_crowns = مجموع تاج‌های گرفته شده
  • total_crowns_lost = مجموع تاج‌های از دست رفته
    ↓
فرمول امتیازدهی:
  score = (total_wins × 3) + (total_draws × 1) + (total_crowns ÷ 10)
    ↓
win_rate محاسبه می‌شود:
  win_rate = (total_wins / total_battles) × 100
    ↓
رتبه‌بندی براساس score مرتب می‌شود
    ↓
rank به هر شرکت‌کننده اختصاص داده می‌شود (1, 2, 3, ...)
    ↓
لیدربورد real-time آماده نمایش است
```

### 6️⃣ چت تورنمنت

```
شرکت‌کنندگان تایید شده می‌توانند در چت گروهی شرکت کنند
    ↓
ارسال پیام:
  POST /api/tournaments/chat/
  {
    "tournament": tournament_id,
    "message": "سلام، موفق باشید!",
    "reply_to": message_id (اختیاری)
  }
    ↓
سیستم چک می‌کند:
  • آیا کاربر شرکت‌کننده تایید شده است؟
  • آیا تورنمنت فعال است؟
    ↓
پیام در دیتابیس ذخیره می‌شود
    ↓
مشاهده چت:
  GET /api/tournaments/chat/tournament/{slug}/
    ↓
فقط شرکت‌کنندگان تایید شده می‌توانند چت را ببینند
    ↓
حذف پیام (توسط فرستنده یا ادمین):
  POST /api/tournaments/chat/{id}/delete-message/
  → is_deleted = True (soft delete)
```

### 7️⃣ پایان تورنمنت

```
زمان پایان تورنمنت می‌رسد
    ↓
ادمین وارد پنل می‌شود و:
  1. آخرین sync بازی‌ها را چک می‌کند
  2. لیدربورد نهایی را بررسی می‌کند
  3. اگر نیاز باشد، بازی‌هایی که is_counted=False دارند را excluded می‌کند
    ↓
دکمه "Finish Tournament" را می‌زند
    ↓
سیستم:
  • وضعیت تورنمنت را به "finished" تغییر می‌دهد
  • end_date = زمان فعلی
  • auto_tracking_enabled = False (توقف sync)
    ↓
رتبه‌بندی نهایی قفل می‌شود
```

### 8️⃣ توزیع جوایز

```
رتبه نهایی هر شرکت‌کننده مشخص شد
    ↓
ادمین جدول توزیع جایزه را مشخص می‌کند:
  مثال برای 8 نفره:
    🥇 رتبه 1: 40% از prize_pool
    🥈 رتبه 2: 25%
    🥉 رتبه 3: 15%
    رتبه 4: 10%
    رتبه 5-8: 2.5% هر کدام
    ↓
کمیسیون پلتفرم کسر می‌شود:
  commission_amount = prize_pool × (platform_commission / 100)
  distributable_pool = prize_pool - commission_amount
    ↓
برای هر برنده:
  prize_amount = distributable_pool × (percentage / 100)
    ↓
  1. TournamentParticipant.prize_won = prize_amount
  2. Wallet.balance += prize_amount
  3. Transaction ثبت می‌شود:
     • transaction_type = "tournament_prize"
     • amount = prize_amount
     • description = "جایزه رتبه X تورنمنت Y"
    ↓
  4. نوتیفیکیشن ارسال می‌شود:
     📧 "تبریک! شما رتبه X را کسب کردید"
     💰 "مبلغ {prize_amount} تومان به کیف پول شما واریز شد"
    ↓
کمیسیون پلتفرم به حساب مدیریت واریز می‌شود
```

### 9️⃣ برداشت جوایز

```
کاربر به کیف پول خود می‌رود
    ↓
موجودی جدید را مشاهده می‌کند
    ↓
دکمه "برداشت" را می‌زند
    ↓
اطلاعات بانکی خود را وارد می‌کند:
  • شماره کارت
  • نام صاحب حساب
    ↓
درخواست برداشت ثبت می‌شود (وضعیت: pending)
    ↓
ادمین در پنل ادمین درخواست را بررسی می‌کند
    ↓
واریز دستی انجام می‌شود
    ↓
ادمین وضعیت را به "completed" تغییر می‌دهد
    ↓
موجودی کاربر کم می‌شود
    ↓
Transaction ثبت می‌شود:
  • transaction_type = "withdrawal"
  • amount = -withdrawal_amount
    ↓
نوتیفیکیشن ارسال می‌شود:
  📧 "برداشت شما با موفقیت انجام شد"
```

### 🔟 آمار و گزارش‌گیری

```
در طول و بعد از تورنمنت، اطلاعات زیر قابل دسترسی است:

برای کاربران:
  • لیدربورد لحظه‌ای
  • تاریخچه بازی‌های خود
  • آمار شخصی (W/L/D، تاج‌ها، win rate)
  • تاریخچه تورنمنت‌ها
  • تاریخچه تراکنش‌ها

برای ادمین:
  • داشبورد کامل تورنمنت
  • لیست تمام بازی‌های sync شده
  • آمار شرکت‌کنندگان
  • گزارش مالی (ورودی‌ها، جوایز، کمیسیون)
  • لاگ کامل همه تراکنش‌ها
  • نمودارها و تحلیل‌ها
```

### ⚠️ نکات مهم

**1. Clash Royale API Limitations:**
- API رسمی Clash Royale فقط read-only است
- نمی‌توان تورنمنت را از طریق API ساخت
- باید manual در بازی ساخت و تگ را در پنل وارد کرد

**2. Battle Log Sync:**
- API فقط 25 بازی اخیر را برمی‌گرداند
- هر 2 دقیقه sync می‌شود تا بازی‌ای از دست نرود
- فیلتر زمانی با tracking_started_at انجام می‌شود

**3. توزیع جوایز:**
- جدول توزیع باید قبل از شروع مشخص شود
- کمیسیون پلتفرم قبل از توزیع کسر می‌شود
- تمام تراکنش‌ها لاگ می‌شوند

**4. امنیت مالی:**
- همه تراکنش‌ها دارای verification هستند
- برداشت‌ها نیاز به تایید ادمین دارند
- تاریخچه کامل تراکنش‌ها حفظ می‌شود

---

## 📁 ساختار پروژه

```
iran_tournament_backend/
│
├── config/                          # تنظیمات اصلی Django
│   ├── settings.py                 # تنظیمات پروژه
│   ├── urls.py                     # URL routing اصلی
│   ├── celery.py                   # تنظیمات Celery
│   └── wsgi.py                     # WSGI configuration
│
├── apps/                            # Django apps
│   │
│   ├── accounts/                   # مدیریت کاربران
│   │   ├── models.py              # User, UserStats, UserWallet
│   │   ├── serializers.py         # API serializers
│   │   ├── views.py               # Authentication, Profile APIs
│   │   ├── tasks.py               # Celery tasks (ranking updates)
│   │   └── admin.py               # Django admin
│   │
│   ├── tournaments/                # مدیریت تورنمنت‌ها
│   │   ├── models.py              # Tournament, Participant, BattleLog, Ranking
│   │   ├── serializers.py         # Tournament APIs serializers
│   │   ├── views.py               # Tournament, BattleLog, Ranking ViewSets
│   │   ├── tasks.py               # Battle sync, notifications (every 2 min)
│   │   ├── admin.py               # Admin panel با UI کامل
│   │   ├── filters.py             # Filtering برای API
│   │   ├── pagination.py          # Custom pagination
│   │   └── services/              # Business logic
│   │       └── clash_royale_client.py  # Clash Royale API client
│   │
│   ├── matches/                    # سیستم مسابقات
│   │   ├── models.py              # Match, Game, Dispute
│   │   ├── serializers.py         # Match APIs
│   │   ├── views.py               # Match management
│   │   ├── tasks.py               # Match reminders
│   │   └── admin.py               # Match admin panel
│   │
│   ├── payments/                   # سیستم پرداخت
│   │   ├── models.py              # Payment, Transaction, Coupon
│   │   ├── serializers.py         # Payment APIs
│   │   ├── views.py               # Payment, Wallet APIs
│   │   ├── tasks.py               # Payment expiry checks
│   │   └── gateways/              # Payment gateway integrations
│   │       ├── zarinpal.py
│   │       ├── idpay.py
│   │       ├── nextpay.py
│   │       └── zibal.py
│   │
│   └── notifications/              # سیستم اعلان‌ها
│       ├── models.py              # Notification, NotificationPreference
│       ├── serializers.py         # Notification APIs
│       ├── views.py               # Notification management
│       ├── tasks.py               # Email/SMS sending, digest
│       └── admin.py               # Notification admin
│
├── media/                          # فایل‌های آپلود شده کاربران
├── staticfiles/                    # فایل‌های static (CSS, JS)
├── logs/                           # فایل‌های log
│
├── requirements.txt                # Python dependencies
├── .env.example                    # نمونه فایل environment variables
├── manage.py                       # Django management script
└── README.md                       # این فایل
```

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها

```bash
Python 3.11+
PostgreSQL 15+ (برای production)
Redis 7+
```

### 1. Clone کردن پروژه

```bash
git clone https://github.com/czmobin/iran_tournament_backend.git
cd iran_tournament_backend
```

### 2. ساخت Virtual Environment

```bash
python -m venv venv

# فعال‌سازی (Linux/macOS)
source venv/bin/activate

# فعال‌سازی (Windows)
venv\Scripts\activate
```

### 3. نصب Dependencies

```bash
pip install -r requirements.txt
```

### 4. تنظیم Environment Variables

```bash
cp .env.example .env
```

فایل `.env` رو باز کن و مقادیر زیر رو تنظیم کن:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (برای Development می‌تونی SQLite استفاده کنی)
DB_ENGINE=sqlite  # یا postgresql
DB_NAME=iran_tournament
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Clash Royale API
CLASH_ROYALE_API_KEY=your-clash-royale-api-key

# Email (اختیاری)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password

# SMS (اختیاری)
SMS_PROVIDER=kavenegar
KAVENEGAR_API_KEY=your-kavenegar-api-key

# Payment Gateways
ZARINPAL_MERCHANT_ID=your-merchant-id
IDPAY_API_KEY=your-idpay-api-key
```

### 5. اجرای Migrations

```bash
python manage.py migrate
```

### 6. ساخت Superuser

```bash
python manage.py createsuperuser
```

### 7. راه‌اندازی Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# چک کردن Redis
redis-cli ping
# باید پاسخ PONG رو بده
```

### 8. راه‌اندازی Celery

در 2 terminal جداگانه:

**Terminal 1 - Celery Worker:**
```bash
celery -A config worker -l info
```

**Terminal 2 - Celery Beat (برای scheduled tasks):**
```bash
celery -A config beat -l info
```

### 9. شروع Django Server

```bash
python manage.py runserver
```

پروژه در آدرس http://localhost:8000 در دسترس خواهد بود.

---

## 🎮 تنظیمات Clash Royale API

### دریافت API Key

1. برو به https://developer.clashroyale.com/
2. ثبت‌نام کن و وارد شو
3. یک API key جدید بساز
4. API key رو در فایل `.env` قرار بده:

```env
CLASH_ROYALE_API_KEY=eyJ0eXAiOiJKV1QiLCJhbGc...
```

### محدودیت‌های API

- **Rate Limit**: معمولاً 1000 درخواست در 10 دقیقه
- **Battle Log**: فقط 25 بازی اخیر قابل دسترسی است
- **Read-Only**: امکان ساخت تورنمنت از طریق API وجود ندارد

### نحوه کار اتصال

1. Admin تورنمنت رو دستی در Clash Royale می‌سازه
2. تگ تورنمنت (مثل `#ABC123`) و رمز رو در Admin Panel Django وارد می‌کنه
3. وقتی تورنمنت شروع می‌شه، سیستم:
   - به همه شرکت‌کنندگان Email/SMS می‌فرسته
   - هر 2 دقیقه battle logs همه بازیکنا رو sync می‌کنه
   - رتبه‌بندی رو به صورت خودکار update می‌کنه

---

## 📊 مدل‌های دیتابیس

### Apps/Accounts

#### **User** (`accounts.User`)
کاربران سیستم با اطلاعات پروفایل و تگ Clash Royale

**فیلدهای مهم:**
- `phone_number` - شماره موبایل (required, unique) ⭐
- `email` - ایمیل (optional)
- `username` - نام کاربری (unique)
- `first_name`, `last_name` - نام و نام خانوادگی
- `clash_royale_tag` - تگ Clash Royale (#ABC123)
- `is_verified` - وضعیت تأیید شده (با OTP)
- `profile_picture` - تصویر پروفایل
- `wallet_balance` - موجودی کیف پول

**⚠️ نکته مهم:**
- احراز هویت فقط با شماره موبایل و OTP انجام می‌شود
- کاربران با `set_unusable_password()` ایجاد می‌شوند (بدون رمز عبور)

#### **UserStats** (`accounts.UserStats`)
آمار عملکرد کاربران در تورنمنت‌ها

**فیلدهای مهم:**
- `tournaments_played` - تعداد تورنمنت‌های شرکت کرده
- `tournaments_won` - تعداد تورنمنت‌های برنده شده
- `total_matches` - تعداد کل مسابقات
- `win_rate` - درصد برد (محاسبه خودکار)
- `ranking` - رتبه کلی

#### **UserWallet** (`accounts.UserWallet`)
کیف پول کاربران

**فیلدهای مهم:**
- `balance` - موجودی کیف پول
- `total_deposit` - مجموع واریزی‌ها
- `total_withdrawal` - مجموع برداشت‌ها

### Apps/Tournaments

#### **Tournament** (`tournaments.Tournament`)
تورنمنت‌های Clash Royale

**فیلدهای مهم:**
- `title` - عنوان
- `game_mode` - حالت بازی (normal, double_elixir, ...)
- `max_participants` - حداکثر شرکت‌کننده
- `entry_fee` - هزینه ورودی
- `prize_pool` - جایزه کل
- `status` - draft, registration, ongoing, finished
- **`clash_royale_tournament_tag`** ⭐ - تگ تورنمنت (#ABC123)
- **`tournament_password`** ⭐ - رمز تورنمنت
- **`auto_tracking_enabled`** ⭐ - ردیابی خودکار فعال؟

#### **TournamentParticipant** (`tournaments.TournamentParticipant`)
شرکت‌کنندگان تورنمنت

**فیلدهای مهم:**
- `tournament` - رابطه با Tournament
- `user` - رابطه با User
- `status` - pending, confirmed, disqualified
- `placement` - رتبه نهایی
- `prize_won` - جایزه برنده شده

#### **PlayerBattleLog** (`tournaments.PlayerBattleLog`) ⭐
لاگ بازی‌های بازیکنان از Clash Royale API

**فیلدهای مهم:**
- `tournament` - رابطه با Tournament
- `participant` - رابطه با Participant
- `battle_time` - زمان بازی (از API)
- `player_tag` - تگ بازیکن
- `player_name` - نام بازیکن
- `player_crowns` - تاج‌های بازیکن
- `opponent_tag` - تگ حریف
- `opponent_crowns` - تاج‌های حریف
- `is_winner` - برنده؟
- `player_cards` - کارت‌های استفاده شده (JSON)
- `raw_battle_data` - داده کامل از API (JSON)

**Unique Constraint:**
```python
unique_together = ['tournament', 'player_tag', 'battle_time', 'opponent_tag']
```

#### **TournamentRanking** (`tournaments.TournamentRanking`) ⭐
رتبه‌بندی real-time بر اساس battle logs

**فیلدهای مهم:**
- `tournament` - رابطه با Tournament
- `participant` - رابطه با Participant
- `rank` - رتبه
- `total_battles` - تعداد کل بازی‌ها
- `total_wins` - تعداد برد
- `win_rate` - درصد برد (محاسبه خودکار)
- `score` - امتیاز (Wins×3 + Draws×1 + Crowns÷10)
- `calculated_at` - زمان محاسبه

**فرمول محاسبه امتیاز:**
```python
score = (total_wins * 3) + (total_draws * 1) + (total_crowns // 10)
```

#### **TournamentChat** (`tournaments.TournamentChat`) ⭐
چت گروهی بین شرکت‌کنندگان تورنمنت

**فیلدهای مهم:**
- `tournament` - رابطه با Tournament
- `sender` - رابطه با User (فرستنده)
- `message` - متن پیام (حداکثر 1000 کاراکتر)
- `reply_to` - پاسخ به پیام دیگر (self FK)
- `is_deleted` - حذف شده؟ (soft delete)
- `deleted_by` - حذف شده توسط
- `deleted_at` - زمان حذف
- `created_at` - زمان ارسال

**محدودیت‌ها:**
- فقط شرکت‌کنندگان تایید شده می‌توانند پیام بفرستند
- فقط در تورنمنت‌های فعال (registration, ready, ongoing) قابل استفاده
- فرستنده، ادمین یا سازنده تورنمنت می‌توانند پیام را حذف کنند

### Apps/Matches

#### **Match** (`matches.Match`)
مسابقات بین بازیکنان

**فیلدهای مهم:**
- `tournament` - رابطه با Tournament
- `player1`, `player2` - بازیکنان
- `winner` - برنده
- `status` - scheduled, ongoing, completed
- `best_of` - Best of 3, 5, 7

#### **Game** (`matches.Game`)
بازی‌های درون یک مسابقه

**فیلدهای مهم:**
- `match` - رابطه با Match
- `winner` - برنده
- `player1_crowns`, `player2_crowns` - تاج‌ها
- `screenshot` - اسکرین‌شات نتیجه
- `is_overtime` - Overtime

### Apps/Payments

#### **Payment** (`payments.Payment`)
پرداخت‌های انجام شده

**فیلدهای مهم:**
- `user` - رابطه با User
- `amount` - مبلغ
- `gateway` - zarinpal, idpay, nextpay, zibal
- `status` - pending, completed, failed, refunded
- `payment_type` - deposit, entry_fee, prize, withdrawal

#### **Transaction** (`payments.Transaction`)
تراکنش‌های کیف پول

**فیلدهای مهم:**
- `wallet` - رابطه با UserWallet
- `transaction_type` - deposit, withdrawal, entry_fee, prize
- `amount` - مبلغ
- `balance_after` - موجودی بعد از تراکنش

---

## 🌐 API Endpoints

### Base URL
```
http://localhost:8000/api/
```

### 🔐 Authentication (OTP-based)

سیستم احراز هویت این پلتفرم بر اساس **شماره موبایل و OTP (کد یکبار مصرف)** است.

#### 📝 فلوی کامل لاگین/رجیستر

```
کاربر شماره موبایل را وارد می‌کند
    ↓
سیستم OTP ارسال می‌کند
    ↓
کاربر کد OTP را وارد می‌کند
    ↓
اگر شماره موجود بود → لاگین (توکن‌ها برگشت داده می‌شود)
اگر شماره جدید بود → فرم تکمیل اطلاعات (username, نام و...)
    ↓
ثبت‌نام کامل می‌شود و توکن‌ها برگشت داده می‌شوند
```

---

#### 1️⃣ ارسال OTP
```http
POST /api/auth/send-otp/
Content-Type: application/json

{
  "phone_number": "09123456789"
}
```

**Response:**
```json
{
  "task_id": "abc-123-def",
  "user_exists": true,
  "message": "کد تایید به شماره شما ارسال شد."
}
```

**یا اگر کاربر جدید باشد:**
```json
{
  "task_id": "abc-123-def",
  "user_exists": false,
  "message": "کد تایید برای ثبت‌نام ارسال شد."
}
```

**Errors:**
- `400 Bad Request`: شماره تلفن وارد نشده / فرمت اشتباه
- `429 Too Many Requests`: باید 5 ثانیه صبر کنید

**⏱️ محدودیت‌ها:**
- Cooldown: 5 ثانیه بین هر درخواست
- OTP timeout: 2 دقیقه

---

#### 2️⃣ تایید OTP و لاگین/رجیستر
```http
POST /api/auth/verify-otp/
Content-Type: application/json

{
  "phone_number": "09123456789",
  "otp": "123456"
}
```

**Response (کاربر موجود - لاگین):**
```json
{
  "action": "login",
  "user": {
    "id": 42,
    "username": "player1",
    "phone_number": "09123456789",
    "email": "player@example.com",
    "first_name": "علی",
    "last_name": "احمدی",
    "clash_royale_tag": "#ABC123",
    "is_verified": true,
    "wallet_balance": "50000.00",
    "created_at": "2025-11-01T10:00:00Z"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "ورود با موفقیت انجام شد."
}
```

**Response (کاربر جدید - نیاز به تکمیل اطلاعات):**
```json
{
  "action": "register",
  "message": "لطفاً اطلاعات ثبت‌نام را تکمیل کنید.",
  "phone_number": "09123456789"
}
```

**Errors:**
- `400 Bad Request`: شماره یا OTP وارد نشده / OTP نادرست
- `503 Service Unavailable`: خطا در SMS Provider

**⏱️ زمان اعتبار OTP:**
- بعد از تایید OTP، 10 دقیقه فرصت برای تکمیل ثبت‌نام

---

#### 3️⃣ تکمیل ثبت‌نام (فقط برای کاربران جدید)
```http
POST /api/auth/complete-registration/
Content-Type: application/json

{
  "phone_number": "09123456789",
  "username": "player1",
  "first_name": "علی",
  "last_name": "احمدی",
  "email": "ali@example.com",          // اختیاری
  "clash_royale_tag": "#ABC123"        // اختیاری
}
```

**Response:**
```json
{
  "user": {
    "id": 43,
    "username": "player1",
    "phone_number": "09123456789",
    "email": "ali@example.com",
    "first_name": "علی",
    "last_name": "احمدی",
    "clash_royale_tag": "#ABC123",
    "is_verified": true,
    "wallet_balance": "0.00",
    "created_at": "2025-11-09T15:30:00Z"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "ثبت‌نام با موفقیت انجام شد."
}
```

**Validation:**
- `phone_number`: الزامی - باید OTP تایید شده باشد
- `username`: الزامی - یونیک
- `first_name`: الزامی
- `last_name`: الزامی
- `email`: اختیاری - اگر وارد شود باید یونیک باشد
- `clash_royale_tag`: اختیاری - فرمت: `#ABC123`

**Errors:**
- `400 Bad Request`: فیلدهای الزامی وارد نشده
- `400 Bad Request`: OTP تایید نشده (10 دقیقه گذشته)
- `400 Bad Request`: username یا email تکراری است

---

#### 4️⃣ Refresh Token
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

#### 5️⃣ خروج (Logout)
```http
POST /api/auth/logout/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "message": "خروج با موفقیت انجام شد."
}
```

---

#### 🔑 استفاده از Token در درخواست‌ها

بعد از لاگین/رجیستر، `access` token را در header درخواست‌ها قرار دهید:

```http
GET /api/tournaments/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**⏱️ زمان اعتبار توکن‌ها:**
- Access Token: 1 ساعت
- Refresh Token: 7 روز

---

#### 📱 دریافت پروفایل کاربر
```http
GET /api/auth/profile/
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": 42,
  "username": "player1",
  "email": "ali@example.com",
  "phone_number": "09123456789",
  "first_name": "علی",
  "last_name": "احمدی",
  "clash_royale_tag": "#ABC123",
  "profile_picture": "/media/profile_pictures/user42.jpg",
  "wallet_balance": "50000.00",
  "is_verified": true,
  "created_at": "2025-11-01T10:00:00Z",
  "stats": {
    "tournaments_played": 15,
    "tournaments_won": 3,
    "total_matches": 120,
    "matches_won": 75,
    "win_rate": 62.50,
    "total_earnings": 500000.00,
    "ranking": 12
  }
}
```

---

#### ⚙️ آپدیت پروفایل
```http
PATCH /api/auth/profile/update/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "first_name": "علی",
  "last_name": "رضایی",
  "clash_royale_tag": "#XYZ789"
}
```

---

#### 🔄 Legacy Endpoints (سازگاری با نسخه قبل)

این endpoint ها همچنان کار می‌کنند اما **توصیه نمی‌شود استفاده شوند**:

```http
POST /api/auth/register/   # ثبت‌نام قدیمی با username/password
POST /api/auth/login/      # لاگین قدیمی با username/password
```

**⚠️ توجه:** برای کاربران جدید، فقط از فلوی OTP استفاده کنید.

### 🏆 Tournaments

#### لیست تورنمنت‌ها
```http
GET /api/tournaments/
GET /api/tournaments/?status=registration
GET /api/tournaments/?game_mode=normal
```

#### جزئیات تورنمنت
```http
GET /api/tournaments/{slug}/
```

#### ثبت‌نام در تورنمنت
```http
POST /api/tournaments/{slug}/register/
Authorization: Bearer {access_token}
```

#### Leaderboard تورنمنت ⭐
```http
GET /api/tournaments/rankings/tournament/{slug}/

Response:
[
  {
    "rank": 1,
    "user": {
      "username": "player1",
      "clash_royale_tag": "#ABC123"
    },
    "total_battles": 15,
    "total_wins": 12,
    "total_losses": 2,
    "win_rate": "80.00",
    "score": 40
  }
]
```

### 🎮 Battle Logs ⭐

#### لیست Battle Logs
```http
GET /api/tournaments/battle-logs/
GET /api/tournaments/battle-logs/?tournament={slug}
```

#### جزئیات یک Battle
```http
GET /api/tournaments/battle-logs/{id}/

Response:
{
  "battle_time": "2025-11-09T14:25:30Z",
  "player_name": "Player1",
  "player_crowns": 3,
  "opponent_name": "Player2",
  "opponent_crowns": 1,
  "is_winner": true,
  "result": "برد",
  "player_cards": [
    {"name": "Hog Rider", "level": 11}
  ]
}
```

#### بازی‌های من
```http
GET /api/tournaments/battle-logs/my-battles/
```

### 💬 Tournament Chat ⭐

#### لیست پیام‌های تورنمنت
```http
GET /api/tournaments/chat/tournament/{slug}/
Authorization: Bearer {access_token}

Response:
{
  "results": [
    {
      "id": 123,
      "sender": {
        "username": "player1",
        "profile_picture": "/media/..."
      },
      "message": "سلام به همه! موفق باشید",
      "reply_to_message": null,
      "created_at": "2025-11-09T15:30:00Z",
      "can_delete": true
    }
  ]
}
```

#### ارسال پیام جدید
```http
POST /api/tournaments/chat/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "tournament": 42,
  "message": "سلام، موفق باشید!",
  "reply_to": 120  // اختیاری - پاسخ به پیام
}

Response:
{
  "id": 124,
  "sender": {...},
  "message": "سلام، موفق باشید!",
  "reply_to_message": {
    "id": 120,
    "sender_username": "player2",
    "message": "چطور می‌تونم به تورنمنت ملحق بشم؟",
    "created_at": "2025-11-09T15:28:00Z"
  },
  "created_at": "2025-11-09T15:30:00Z"
}
```

#### حذف پیام
```http
POST /api/tournaments/chat/{id}/delete-message/
Authorization: Bearer {access_token}

Response:
{
  "message": "پیام با موفقیت حذف شد"
}
```

**محدودیت‌ها:**
- فقط شرکت‌کنندگان تایید شده می‌توانند چت را ببینند و پیام بفرستند
- پیام‌ها فقط در تورنمنت‌های فعال قابل ارسال هستند
- حذف پیام توسط فرستنده، ادمین یا سازنده تورنمنت امکان‌پذیر است

### 💰 Payments & Wallet

#### موجودی کیف پول
```http
GET /api/payments/wallet/
```

#### واریز به کیف پول
```http
POST /api/payments/deposit/

{
  "amount": 100000,
  "gateway": "zarinpal"
}
```

---

## ⚙️ Celery Tasks

### Scheduled Tasks (Celery Beat)

#### **هر 2 دقیقه**: Sync Battle Logs ⭐
```python
Task: apps.tournaments.tasks.sync_tournament_battle_logs
Schedule: */2 * * * *

کارها:
- پیدا کردن تورنمنت‌های فعال با auto_tracking_enabled=True
- دریافت battle logs از Clash Royale API برای همه شرکت‌کنندگان
- ذخیره فقط بازی‌هایی که بعد از tracking_started_at بودن
- Update کردن leaderboard
```

#### **هر دقیقه**: چک کردن شروع تورنمنت‌ها
```python
Task: apps.tournaments.tasks.check_tournament_start_times
Schedule: * * * * *

کارها:
- پیدا کردن تورنمنت‌هایی که باید شروع بشن
- تغییر status به 'ongoing'
- فعال کردن auto_tracking
- ارسال Email/SMS به شرکت‌کنندگان
```

#### **هر 5 دقیقه**: بررسی پرداخت‌های منقضی شده
```python
Task: apps.payments.tasks.expire_old_payments
Schedule: */5 * * * *
```

#### **هر 5 دقیقه**: یادآوری مسابقات
```python
Task: apps.matches.tasks.send_match_reminders
Schedule: */5 * * * *
```

---

## 🎛 Admin Panel

### دسترسی
```
http://localhost:8000/admin/
```

### امکانات Admin

#### **Tournaments**
- ✅ مدیریت کامل تورنمنت‌ها
- ✅ وارد کردن تگ و رمز Clash Royale
- ✅ نمایش آمار با badge های رنگی
- ✅ Action: شروع، پایان، لغو تورنمنت
- ✅ Inline editing برای شرکت‌کنندگان

#### **Battle Logs** ⭐
- ✅ لیست تمام بازی‌ها
- ✅ Badge رنگی برای نتایج (✓ برد،✗ باخت، = مساوی)
- ✅ فیلتر بر اساس تورنمنت، نوع بازی، نتیجه
- ✅ جزئیات کامل شامل کارت‌ها و HP برج‌ها

#### **Rankings** ⭐
- ✅ نمایش با مدال‌ها (🥇🥈🥉)
- ✅ آمار کامل (W/L/D, Win Rate, Score)
- ✅ Action: محاسبه مجدد رتبه‌بندی
- ✅ رنگ‌بندی براساس Win Rate

---

## 📖 نمونه استفاده

### Scenario: برگزاری تورنمنت با Clash Royale Tracking

#### 1️⃣ ساخت تورنمنت در Django
```
Admin Panel → Tournaments → Add Tournament
- Title: "تورنمنت هفتگی"
- Game Mode: Normal
- Start Date: 2025-11-10 20:00
```

#### 2️⃣ ساخت تورنمنت در Clash Royale
```
Clash Royale → Tournaments → Create
- Name: "تورنمنت هفتگی"
- Password: "PASS123"
- Note Tournament Tag: #ABC123XYZ
```

#### 3️⃣ اتصال به Django
```
Admin Panel → Edit Tournament
- Clash Royale Tournament Tag: #ABC123XYZ
- Tournament Password: PASS123
- Save
```

#### 4️⃣ شروع خودکار
```
وقتی start_date فرا می‌رسه:
✅ Email/SMS به شرکت‌کنندگان
✅ Auto tracking فعال می‌شه
✅ هر 2 دقیقه battle logs sync می‌شه
```

#### 5️⃣ مشاهده Leaderboard
```http
GET /api/tournaments/rankings/tournament/tornoment-haftegi/
```

---

## 🚀 Deployment

### Production Checklist

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` امن و تصادفی
- [ ] `ALLOWED_HOSTS` تنظیم شده
- [ ] استفاده از PostgreSQL
- [ ] تنظیم HTTPS
- [ ] Static files جمع‌آوری شده
- [ ] Redis برای Cache و Celery
- [ ] Celery Worker و Beat
- [ ] Nginx/Apache برای Reverse Proxy

### دستورات Production

```bash
# Static Files
python manage.py collectstatic --noinput

# Migrations
python manage.py migrate

# Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Celery
celery -A config worker -l info --concurrency=4
celery -A config beat -l info
```

---

## 📄 License

این پروژه تحت لایسنس MIT منتشر شده است.

---

**ساخته شده با ❤️ برای کامیونیتی Clash Royale ایران**
