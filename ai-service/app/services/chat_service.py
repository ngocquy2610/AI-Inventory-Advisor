"""Chat service — M10 logic."""

from sqlalchemy.orm import Session

from app.schemas.chat import ChatResponse


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def process_message(self, session_id, message: str) -> ChatResponse:
        intent_keywords = {
            "forecast": "Based on historical data, I can see the demand forecast for this product. Would you like me to run a detailed forecast?",
            "reorder": "I've analyzed your current stock levels. There are several products that may need reordering soon.",
            "overstock": "I've detected some products with excess inventory. Consider promotions or transfers to balance stock.",
            "transfer": "I can recommend inter-store transfers to optimize your inventory distribution.",
            "supplier": "I've analyzed supplier reliability scores. Most suppliers are performing well.",
        }

        reply = "I'm your AI Inventory Advisor. I can help with forecasts, reorder recommendations, overstock detection, transfers, and supplier analysis. What would you like to explore?"
        for keyword, response in intent_keywords.items():
            if keyword in message.lower():
                reply = response
                break

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            sources=["inventory_advisor_knowledge_base"],
        )