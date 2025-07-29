<!-- llm-chatbot/
├── app.py                            # จุดเริ่มต้นของแอปฯ สำหรับรับข้อความและส่งเข้า workflow graph
├── config/
│   ├── settings.py                   # เก็บ environment variables, API key, config ทั่วไป
│   └── workflow_default.yaml         # ไฟล์ config สำหรับนิยาม workflow graph (node/edge/condition)
├── adapters/
│   ├── line_adapter.py               # logic สำหรับรับ/ส่งข้อความกับ LINE (webhook, reply, format)
│   └── platform_base.py              # base class/interface สำหรับรองรับ platform อื่นๆ ในอนาคต
├── bot_gateway/
│   └── gateway.py                    # orchestration layer: ประสานงานระหว่าง adapter, session, workflow
├── session/
│   ├── session_manager.py            # จัดการโหลด/บันทึก session & context ของแต่ละ user
│   ├── store_redis.py                # ตัวอย่าง backend สำหรับ session (ใช้ Redis)
│   └── context_schema.py             # โครงสร้างข้อมูล context ที่ใช้วนใน workflow
├── llm/
│   ├── llm_service.py                # รวม logic เรียก LLM pipeline (prompt, postprocess)
│   ├── prompt_strategy.py            # สร้าง prompt template ตาม use case
│   ├── postprocess_strategy.py       # จัดการ postprocess เช่น enrich, format, translation
│   └── llm_api.py                    # เรียกใช้งาน LLM engine (OpenAI, Local, ฯลฯ)
├── user/
│   └── profile_service.py            # ดึงและจัดการ user profile (display name, picture, ฯลฯ)
├── utils/
│   ├── logger.py                     # logging utility สำหรับ debug และ monitoring
│   └── event_bus.py                  # pub/sub หรือ observer สำหรับ event ต่างๆ (analytics, handoff)
├── analytics/
│   └── metrics_collector.py          # เก็บ/ส่ง metrics, event, user engagement สำหรับ dashboard
├── workflow/
│   ├── graph_loader.py               # โหลดและสร้าง workflow graph จากไฟล์ config (YAML)
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── preprocess_node.py        # node สำหรับ preprocess ข้อความ (clean, normalize)
│   │   ├── intent_node.py            # node สำหรับ intent classification (หาเจตนา user)
│   │   ├── llm_node.py               # node สำหรับเรียก LLM model
│   │   ├── postprocess_node.py       # node สำหรับ postprocess ข้อความก่อนส่งกลับ user
│   │   └── human_handoff_node.py     # node สำหรับ human handoff (เชื่อมต่อเจ้าหน้าที่)
├── requirements.txt                  # รายการ python dependency ทั้งหมดที่ใช้
└── tests/
    └── test_workflow_graph.py        # unit test สำหรับ workflow graph และแต่ละ node
หมายเหตุ
	•	โฟลเดอร์ workflow/nodes/: เพิ่ม node ใหม่ได้ง่าย เช่น profanity_check_node.py, db_lookup_node.py	•	config/workflow_default.yaml: ปรับ flow ได้โดยไม่ต้องแก้โค้ด (เพิ่ม/ลด node, branching)	•	session/: รองรับ context-aware, multi-turn, หรือ personalized bot	•	adapters/: รองรับหลาย platform ได้ในอนาคต	•	llm/: แยก logic LLM ออกจาก workflow, ทำให้เปลี่ยน model หรือ provider ได้ง่าย	•	analytics/: ต่อยอดทำ dashboard, monitor, หรือ A/B test ได้ -->
```mermaid
flowchart TD
    subgraph Platform Layer
        A1[LINE Platform]
        A2[Facebook Messenger]
        A3[Web Chat]
    end

    subgraph Adapter Layer
        B1[LineAdapter]
        B2[FacebookAdapter]
        B3[WebAdapter]
    end

    subgraph Gateway Layer
        C1[BotGateway]
    end

    subgraph Session Layer
        D1[SessionManager]
        D2[Session Store]
    end

    subgraph User/Analytics Layer
        G1[ProfileService]
        G2[MetricsCollector]
    end

    subgraph Workflow Layer
        E1[Workflow Graph]
        E2[PreprocessNode]
        E3[IntentNode]
        E4[LLMNode]
        E5[PostprocessNode]
        E6[HumanHandoffNode]
    end

    subgraph LLM Layer
        F1[PromptStrategy]
        F2[LLM API]
        F3[PostprocessStrategy]
    end

    %% Platform to Adapter
    A1 --> B1
    A2 --> B2
    A3 --> B3

    %% Adapter to Gateway
    B1 --> C1
    B2 --> C1
    B3 --> C1

    %% Gateway to Session
    C1 --> D1
    D1 --> D2
    D2 --> D1
    D1 --> C1

    %% Gateway to User/Analytics
    C1 -- pulls profile --> G1
    C1 -- sends metrics --> G2

    %% Gateway to Workflow
    C1 --> E1
    E1 --> E2
    E2 --> E3
    E3 --> E4
    E4 --> F1
    F1 --> F2
    F2 --> F3
    F3 --> E4
    E4 --> E5
    E5 --> E6
    E6 --> E1
    E1 --> C1

    %% Gateway to Adapter (reply)
    C1 --> B1
    C1 --> B2
    C1 --> B3

    %% Adapter to Platform (reply)
    B1 --> A1
    B2 --> A2
    B3 --> A3
```


uv run python main.py