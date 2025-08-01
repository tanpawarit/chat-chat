"""
AI-Optimized Prompt Templates with XML-style structure for better LLM comprehension.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PromptSection:
    """Represents a section of a prompt with structured content."""

    tag: str
    content: str
    is_list: bool = False


class BasePromptTemplate:
    """Base class for structured prompt templates."""

    def __init__(self):
        self.sections: list[PromptSection] = []

    def add_section(self, tag: str, content: str, is_list: bool = False) -> None:
        """Add a section to the prompt."""
        self.sections.append(PromptSection(tag, content, is_list))

    def render(self) -> str:
        """Render the prompt with XML-style tags."""
        parts = []
        for section in self.sections:
            content = section.content  # Same content regardless of is_list flag

            parts.append(f"<{section.tag}>")
            parts.append(content)
            parts.append(f"</{section.tag}>")

        return "\n".join(parts)


class SystemPromptBuilder:
    """Builder for creating structured system prompts."""

    @staticmethod
    def build_customer_service_prompt() -> str:
        """Build AI-optimized customer service system prompt."""

        template = BasePromptTemplate()

        # System Identity
        template.add_section(
            "system_identity",
            "คุณเป็นผู้เชี่ยวชาญการบริการลูกค้าระดับมืออาชีพ ที่มีความเข้าใจลึกในธุรกิจและสามารถให้คำแนะนำที่เป็นประโยชน์",
        )

        # Core Capabilities
        capabilities = [
            "• วิเคราะห์ความต้องการลูกค้าได้แม่นยำ",
            "• ตอบคำถามด้วยข้อมูลที่ถูกต้องและครบถ้วน",
            "• ปรับภาษาและโทนเสียงตามประเภทลูกค้า",
            "• จัดการสถานการณ์ยุ่งยากได้อย่างมืออาชีพ",
            "• สร้างประสบการณ์ที่ดีให้กับลูกค้าทุกครั้ง",
        ]
        template.add_section("core_capabilities", "\n".join(capabilities))

        # Communication Guidelines
        guidelines = [
            "1. ใช้ภาษาไทยที่สุภาพ เป็นมิตรแต่มีมาตรฐาน",
            '2. เรียกลูกค้าด้วย "คุณ" และปิดท้ายด้วย "ค่ะ"',
            "3. แสดงความเข้าใจและความห่วงใยอย่างจริงใจ",
            "4. ให้คำตอบที่ชัดเจน ตรงประเด็น และเป็นประโยชน์",
            "5. หากไม่แน่ใจ ให้สื่อสารอย่างซื่อสัตย์และเสนอทางเลือก",
            "6. ใช้คำถามเพิ่มเติมเพื่อเข้าใจความต้องการให้ชัดเจน",
        ]
        template.add_section("communication_guidelines", "\n".join(guidelines))

        # Context Processing Rules
        context_rules = [
            "• ใช้ข้อมูลประวัติการสนทนาเพื่อความต่อเนื่อง",
            "• พิจารณาข้อมูลส่วนตัวของลูกค้าในการปรับคำตอบ",
            "• นำเหตุการณ์สำคัญมาประกอบการให้คำแนะนำ",
            "• เชื่อมโยงบริบทปัจจุบันกับข้อมูลที่มีอยู่",
            "• รักษาความสม่ำเสมอในการให้บริการ",
        ]
        template.add_section("context_processing_rules", "\n".join(context_rules))

        # Output Specifications
        output_specs = [
            "• ตอบเป็นข้อความที่อ่านง่าย ความยาวเหมาะสม",
            "• ใช้ emoji เมื่อช่วยสื่อความหมาย (😊 🙏 ✨ 💡)",
            "• แบ่งย่อหน้าเมื่อมีหัวข้อหลายเรื่อง",
            "• ใช้ bullet points เมื่อมีรายการ",
            "• หลีกเลี่ยงข้อความที่ยาวเกินไปในครั้งเดียว",
        ]
        template.add_section("output_specifications", "\n".join(output_specs))

        return template.render()


class ContextInjector:
    """Handles dynamic context injection into prompts."""

    @staticmethod
    def build_user_profile_context(memory_context: dict[str, Any]) -> str:
        """Build user profile context section."""
        if not memory_context.get("user_attributes"):
            return ""

        attributes = memory_context["user_attributes"]
        context_parts = []

        if attributes.get("preferred_language"):
            context_parts.append(f"- ภาษาที่ใช้: {attributes['preferred_language']}")

        if attributes.get("customer_segment"):
            context_parts.append(f"- ประเภทลูกค้า: {attributes['customer_segment']}")

        if attributes.get("timezone"):
            context_parts.append(f"- เขตเวลา: {attributes['timezone']}")

        if not context_parts:
            return ""

        return f"<user_profile>\n{chr(10).join(context_parts)}\n</user_profile>"

    @staticmethod
    def build_conversation_history(memory_context: dict[str, Any]) -> str:
        """Build conversation history context."""
        context_parts = []

        # Recent messages
        recent_messages = memory_context.get("recent_messages", [])
        if recent_messages:
            message_parts = ["<recent_messages>"]
            for msg in recent_messages[-5:]:  # Last 5 messages
                role = "ลูกค้า" if msg["role"] == "user" else "พนักงาน"
                message_parts.append(f"{role}: {msg['message']}")
            message_parts.append("</recent_messages>")
            context_parts.append("\n".join(message_parts))

        # Important events
        if memory_context.get("important_events"):
            event_parts = ["<important_events>"]
            for event in memory_context["important_events"][-3:]:  # Last 3 events
                event_type = event["type"]
                timestamp = event["timestamp"]
                payload = event.get("payload", {})

                if payload and isinstance(payload, dict):
                    content_parts = []

                    # Extract meaningful content from payload
                    if event_type == "REQUEST":
                        if payload.get("original_message"):
                            content_parts.append(
                                f"ข้อความ: '{payload['original_message']}'"
                            )
                        if payload.get("request_type"):
                            content_parts.append(f"ประเภท: {payload['request_type']}")
                        if payload.get("specifics"):
                            content_parts.append(f"รายละเอียด: {payload['specifics']}")

                    elif event_type == "TRANSACTION":
                        if payload.get("original_message"):
                            content_parts.append(
                                f"ข้อความ: '{payload['original_message']}'"
                            )
                        if payload.get("transaction_type"):
                            content_parts.append(
                                f"ประเภท: {payload['transaction_type']}"
                            )
                        if payload.get("stage"):
                            content_parts.append(f"ขั้นตอน: {payload['stage']}")

                    if content_parts:
                        event_parts.append(
                            f"- {event_type}: {', '.join(content_parts)} ({timestamp})"
                        )
                    else:
                        event_parts.append(f"- {event_type}: {timestamp}")
                else:
                    event_parts.append(f"- {event_type}: {timestamp}")

            event_parts.append("</important_events>")
            context_parts.append("\n".join(event_parts))

        # Session variables
        session_vars = memory_context.get("session_variables", {})
        if session_vars.get("current_topic"):
            context_parts.append(
                f"<session_state>\nหัวข้อปัจจุบัน: {session_vars['current_topic']}\n</session_state>"
            )

        # History summary
        if memory_context.get("history_summary"):
            context_parts.append(
                f"<conversation_summary>\n{memory_context['history_summary']}\n</conversation_summary>"
            )

        if not context_parts:
            return ""

        return f"<conversation_context>\n{chr(10).join(context_parts)}\n</conversation_context>"

    @staticmethod
    def build_current_request(user_message: str) -> str:
        """Build current request section."""
        return f"""<current_request>
                ลูกค้าส่งข้อความใหม่: "{user_message}"

                กรุณาตอบกลับอย่างเหมาะสม โดยคำนึงถึงบริบททั้งหมดข้างต้น และให้คำตอบที่เป็นประโยชน์
                </current_request>"""


class PromptValidator:
    """Validates prompt structure and content."""

    @staticmethod
    def validate_xml_structure(prompt: str) -> bool:
        """Check if prompt has proper XML-style structure."""
        # Simple validation - check for opening and closing tags
        lines = prompt.split("\n")
        tag_stack = []

        for line in lines:
            line = line.strip()
            if line.startswith("<") and line.endswith(">"):
                if line.startswith("</"):
                    # Closing tag
                    tag_name = line[2:-1]
                    if tag_stack and tag_stack[-1] == tag_name:
                        tag_stack.pop()
                    else:
                        return False
                else:
                    # Opening tag
                    tag_name = line[1:-1]
                    tag_stack.append(tag_name)

        return len(tag_stack) == 0

    @staticmethod
    def estimate_token_count(prompt: str) -> int:
        """Rough estimation of token count."""
        # Rough approximation: 1 token ≈ 4 characters for Thai/English mixed text
        return len(prompt) // 4


# Pre-built templates
CUSTOMER_SERVICE_SYSTEM_PROMPT = SystemPromptBuilder.build_customer_service_prompt()

# Token-Efficient Event Classification with Structured Output
EVENT_CLASSIFICATION_SYSTEM_PROMPT = """<system_identity>
ผู้เชี่ยวชาญวิเคราะห์การสนทนา จัดประเภทเหตุการณ์และประเมินความสำคัญ
</system_identity>

<event_types>
• INQUIRY: ?, คำถาม, สอบถาม → {"question_type": "", "topic": "", "urgency": ""}
• FEEDBACK: ดี, แย่, ชอบ, รีวิว → {"sentiment": "positive/negative/neutral", "category": ""}
• REQUEST: ขอ, ต้องการ, จอง → {"request_type": "", "urgency": "", "specifics": ""}
• COMPLAINT: ปัญหา, เสีย, ร้องเรียน → {"issue_type": "", "severity": "", "category": ""}
• TRANSACTION: ซื้อ, จ่าย, ราคา → {"transaction_type": "", "stage": "", "amount_mentioned": ""}
• SUPPORT: ช่วย, แนะนำ, วิธี → {"help_type": "", "complexity": "", "topic": ""}
• INFORMATION: แจ้ง, บอก → {"info_type": "", "category": "", "relevance": ""}
• GENERIC_EVENT: สวัสดี, ขอบคุณ → {"conversation_type": "", "politeness_level": ""}
</event_types>

<importance_scale>
• 0.9-1.0: ธุรกรรม, ปัญหาวิกฤต • 0.7-0.8: คำขอสำคัญ, ฟีดแบ็ค
• 0.5-0.6: ขอความช่วยเหลือ • 0.3-0.4: คำถามง่าย • 0.1-0.2: ทักทาย, สังคม
</importance_scale>

<output_format>
ตอบ JSON ตาม EventClassification schema เท่านั้น:
{
  "event_type": "ประเภทข้างต้น",
  "importance_score": 0.0-1.0,
  "payload": {"key": "value"},
  "reasoning": "เหตุผลสั้นๆ"
}
</output_format>"""
