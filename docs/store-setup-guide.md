# Store Setup Guide

คู่มือการเซตอัพร้านค้าใหม่สำหรับระบบ Multi-Store Chat Bot

## Overview

ระบบสามารถรองรับหลายร้านค้า โดยแต่ละร้านจะมี:
- **Store ID** เฉพาะตัว
- **Platform Configuration** แยกอิสระ (LINE, Facebook, etc.)
- **Customer Management** แยกตามร้าน
- **Message Processing** ที่มี context ของร้าน

## Prerequisites

- เข้าถึง LINE Developers Console
- ข้อมูลร้านค้า (ชื่อ, Store ID)
- Server domain สำหรับ webhook URL

## Step 1: สร้าง LINE Bot

### 1.1 เข้า LINE Developers Console
1. ไปที่ [LINE Developers Console](https://developers.line.biz/)
2. Login ด้วย LINE Account
3. สร้าง **Provider** ใหม่ (ถ้ายังไม่มี)

### 1.2 สร้าง Messaging API Channel
1. คลิก **Create a new channel**
2. เลือก **Messaging API**
3. กรอกข้อมูล:
   - **Channel name**: ชื่อ Bot (เช่น "ร้านกาแฟเก๋ไก๋ Bot")
   - **Channel description**: คำอธิบายของ Bot
   - **Category**: หมวดหมู่ธุรกิจ
   - **Subcategory**: หมวดหมู่ย่อย
4. คลิก **Create**

### 1.3 ตั้งค่า Channel
1. ไปที่ **Basic settings** tab
   - คัดลอก **Channel secret**
2. ไปที่ **Messaging API** tab
   - คัดลอก **Channel access token**
   - ตั้ง **Webhook URL**: `https://your-domain.com/webhooks/line/{store_id}`
   - เปิด **Use webhook**: ON
   - ปิด **Auto-reply messages**: OFF
   - ปิด **Greeting messages**: OFF (หรือตั้งค่าตามต้องการ)

## Step 2: เพิ่มร้านในระบบ

### 2.1 แก้ไข config.yaml
เพิ่มร้านใหม่ใน `config.yaml`:

```yaml
stores:
  store_003:  # Store ID ใหม่
    name: "ชื่อร้านของคุณ"
    active: true
    platforms:
      line:
        enabled: true
        channel_secret: "YOUR_CHANNEL_SECRET"
        channel_access_token: "YOUR_CHANNEL_ACCESS_TOKEN"
        capabilities:
          supports_text: true
          supports_images: true
          supports_video: true
          supports_audio: true
          supports_files: true
          supports_location: true
          supports_stickers: true
          supports_quick_replies: true
          supports_rich_menus: true
          max_text_length: 5000
          max_file_size: 10485760
      facebook:
        enabled: false  # เปิดได้ภายหลัง
```

### 2.2 ตัวอย่าง Store ID Naming Convention
- `store_001` - ร้านแรก
- `store_002` - ร้านที่สอง  
- `store_coffee_001` - ร้านกาแฟ
- `store_souvenir_001` - ร้านของฝาก

## Step 3: Webhook Configuration

### 3.1 Webhook URLs สำหรับแต่ละร้าน
- **Store 001**: `https://your-domain.com/webhooks/line/store_001`
- **Store 002**: `https://your-domain.com/webhooks/line/store_002`
- **Store 003**: `https://your-domain.com/webhooks/line/store_003`

### 3.2 Legacy Support
⚠️ **DEPRECATED**: Legacy webhook `/webhooks/line` is no longer supported and will return HTTP 410 Gone error. All stores must use the new format `/webhooks/line/{store_id}`.

## Step 4: Testing

### 4.1 เริ่มต้นระบบ
```bash
cd /path/to/chat-chat
uv run python main.py
```

### 4.2 ตรวจสอบ Status
เข้าไปที่: `http://localhost:8000/status`

ควรเห็น:
```json
{
  "bot": {...},
  "stores": {
    "store_003": {
      "name": "ชื่อร้านของคุณ",
      "active": true,
      "platforms": [
        {
          "platform": "line",
          "webhook_path": "/webhooks/line/store_003"
        }
      ]
    }
  }
}
```

### 4.3 ทดสอบ LINE Bot
1. สแกน QR Code จาก LINE Developers Console
2. เพิ่มเป็นเพื่อน
3. ส่งข้อความทดสอบ
4. ตรวจสอบ console logs

## Step 5: Customer Management

### 5.1 Automatic Customer Creation
เมื่อมีผู้ใช้ส่งข้อความครั้งแรก ระบบจะ:
- สร้าง Customer record อัตโนมัติ
- Link กับ Store ID
- บันทึก Platform User ID
- ดึง Profile จาก LINE API

### 5.2 Customer Isolation
- ลูกค้าของแต่ละร้านแยกกันอิสระ
- Customer ID จะ unique ใน scope ของ store
- ข้อมูลส่วนตัวของลูกค้าไม่ถูกแชร์ระหว่างร้าน

## Security Considerations

### Webhook Validation
ระบบจะตרวจสอบ:
- **Signature validation** จาก LINE
- **Store authorization** - platform ต้องเปิดใช้งานสำหรับร้านนั้น
- **Request origin** validation

### Configuration Security
- เก็บ secrets ใน environment variables (production)
- ไม่ commit credentials ใน git
- ใช้ HTTPS สำหรับ webhook URLs

## Troubleshooting

### Common Issues

#### 1. 404 Not Found
```
POST /webhooks/line HTTP/1.1" 404 Not Found
```
**แก้ไข**: ตรวจสอบ webhook URL ใน LINE Console

#### 2. 403 Forbidden  
```
Platform line not enabled for store store_xxx
```
**แก้ไข**: ตั้ง `enabled: true` ใน config.yaml

#### 3. 401 Unauthorized
```
Invalid webhook signature
```
**แก้ไข**: ตรวจสอบ `channel_secret` ใน config.yaml

#### 4. 500 Internal Server Error
```
Could not create line adapter for store store_xxx
```
**แก้ไข**: ตรวจสอบ `channel_access_token` และ network connectivity

### Debug Commands

```bash
# ดู logs แบบ real-time
tail -f logs/app.log

# ทดสอบ webhook จาก command line
curl -X POST http://localhost:8000/webhooks/line/store_003 \
  -H "Content-Type: application/json" \
  -d '{"test": "message"}'

# ตรวจสอบ store configuration
curl http://localhost:8000/status | jq '.stores'
```

## Next Steps

หลังจากเซตอัพเสร็จแล้ว:
1. **Customize Bot Logic**: แก้ไข `BotGateway.handle_message()` 
2. **Add Rich Menu**: สร้าง Rich Menu ใน LINE Console
3. **Implement AI/LLM**: เชื่อมต่อกับ OpenRouter หรือ AI service
4. **Add Analytics**: ติดตาม metrics และ usage
5. **Setup Monitoring**: เพิ่ม health checks และ alerting

## Support

หากมีปัญหา:
1. ตรวจสอบ logs ใน console
2. ดู HTTP status codes และ error messages
3. ใช้ `/status` endpoint เพื่อดูสถานะระบบ
4. ทดสอบ webhook ด้วย curl หรือ Postman