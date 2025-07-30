```mermaid
flowchart TD
    A1[User sends message]
    B1{Session expired?}
    C1[Fetch events from LT memory]
    C2[Summarize with cheap LLM]
    C3[Create session with summary]
    D1[Load session/context]
    D2[Add user message to history]
    E1[Prepare summary + N recent messages]
    E2{Cache hit?}
    E3[Return cached response]
    E4[Build prompt]
    E5[Send prompt to LLM]
    E6[Receive LLM response]
    F1[Add bot message to history]
    F2[Update session/context]
    F3[Save session/context]
    F4[Reply to user]
    F5{Is important event?}
    F6[Save event to LT memory]

    A1 --> B1
    B1 -- Yes --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    B1 -- No --> D1
    D1 --> D2
    D2 --> E1
    E1 --> E2
    E2 -- Yes --> E3
    E3 --> F1
    E2 -- No --> E4
    E4 --> E5
    E5 --> E6
    E6 --> F1
    F1 --> F2
    F2 --> F3
    F3 --> F4
    F1 --> F5
    F5 -- Yes --> F6
    F5 -- No --> F4
```

คำอธิบาย node เพิ่มเติม (mapping สำหรับ multi-tenant)

### Node Descriptions

* **User sends message**: รับ message พร้อมข้อมูล shop_id, user_id
* **Session expired?**: ตรวจสอบ session key = shop_id:user_id
* **Fetch events from LT memory**: ดึง important events ของ shop_id, user_id
* **Summarize with cheap LLM**: สรุป event/history ด้วย LLM ราคาถูก
* **Create session with summary**: สร้าง session context ใหม่ (shop_id, user_id)
* **Load session/context**: โหลด session/context เดิม (shop_id, user_id)
* **Add user message to history**: เพิ่มข้อความ user ลงใน history
* **Prepare summary + N recent messages**: เตรียมข้อมูลสำหรับ prompt
* **Cache hit?**: เช็ค cache (key = shop_id:user_id:context)
* **Return cached response**: ถ้ามี response เดิมใน cache
* **Build prompt**: สร้าง prompt (inject config, knowledge, policy ของร้าน)
* **Send prompt to LLM**: ส่ง prompt เข้า LLM
* **Receive LLM response**: รับผลลัพธ์จาก LLM
* **Add bot message to history**: เพิ่มข้อความ bot ลงใน history
* **Update session/context**: อัปเดต context
* **Save session/context**: บันทึก session/context
* **Reply to user**: ส่งข้อความกลับ user ที่ร้านค้านั้น
* **Is important event?**: ตรวจสอบ event สำคัญ (ตาม config ร้าน)
* **Save event to LT memory**: เก็บ event ลง LT memory (shop_id, user_id)
