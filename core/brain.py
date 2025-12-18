import config_trinity
import anthropic
import google.generativeai as genai
from openai import OpenAI
from typing import Generator


class TrinityBrain:
    """
    The Trinity Brain: coordinates three AI models for scenario generation and simulation.
    - Writer (Claude): Generates scenarios with streaming
    - Judge (Gemini): Audits and evaluates scenarios
    - Simulator (Local Llama): Handles chat simulations with streaming
    """

    def __init__(self):
        """Initialize the three AI clients with error handling."""
        # 1. The Writer (Claude via Anthropic)
        self.writer_client = None
        try:
            if config_trinity.ANTHROPIC_API_KEY:
                self.writer_client = anthropic.Anthropic(
                    api_key=config_trinity.ANTHROPIC_API_KEY
                )
            else:
                print("⚠️  Warning: ANTHROPIC_API_KEY not set. Writer (Claude) will be unavailable.")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Anthropic client: {e}")

        # 2. The Judge (Gemini via Google)
        self.judge_client = None
        try:
            if config_trinity.GOOGLE_API_KEY:
                genai.configure(api_key=config_trinity.GOOGLE_API_KEY)
                self.judge_client = genai.GenerativeModel(config_trinity.JUDGE_MODEL_NAME)
            else:
                print("⚠️  Warning: GOOGLE_API_KEY not set. Judge (Gemini) will be unavailable.")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Google client: {e}")

        # 3. The Simulator (Local Llama via OpenAI-compatible API)
        self.simulator_client = None
        try:
            self.simulator_client = OpenAI(
                base_url=config_trinity.LOCAL_BASE_URL,
                api_key=config_trinity.LOCAL_API_KEY
            )
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize local OpenAI client: {e}")

    def generate_scenario_stream(self, prompt: str) -> Generator[str, None, None]:
        """
        Generate a scenario using the Writer (Claude) with real-time streaming.

        This method streams text as it's generated, allowing users to see the
        scenario being written in real-time instead of waiting 30+ seconds.

        Args:
            prompt: The prompt describing what scenario to generate

        Yields:
            Text chunks as they are generated in real-time

        Raises:
            RuntimeError: If writer client is not initialized
        """
        if not self.writer_client:
            raise RuntimeError("Writer (Anthropic) client not initialized. Check ANTHROPIC_API_KEY.")

        # System prompt for security scenario generation in Hebrew
        system_prompt = """אתה מומחה לכתיבת תרחישי אבטחה למערכות תחבורה ציבורית בישראל.

תפקידך: ליצור תרחישי הכשרה מציאותיים ומפורטים לצוותי אבטחה, בעברית, בפורמט Markdown.

**פורמט חובה:**

```markdown
# [כותרת התרחיש בעברית]

רמת מורכבות: [נמוכה/בינונית/גבוהה]
נוהל פתיחה באש: [Yes/No]
שימוש במסכה: [Yes/No]
קטגוריה: [שם הקטגוריה]
רמת סיכון: [נמוכה/בינונית/גבוהה/גבוהה מאוד]
רמת סבירות: [נמוכה/בינונית/גבוהה]

**📋 סיפור מקרה:**

[תיאור מפורט של האירוע - מי, מה, איפה, מתי, למה. כתוב בפסקאות קצרות וברורות]

**🎯 שלבי תגובה:**

[רשימה ממוספרת או תבליטים של שלבי התגובה הנדרשים]

**🔫 נוהל פתיחה באש:**

[הסבר מתי מותר/אסור לפתוח באש, או "לא רלוונטי"]

**😷 שימוש במסכה:**

[הסבר האם נדרש שימוש במסכת גז ומדוע]

**🎥 רקע מבצעי:**

[מידע רקע רלוונטי, או "ללא"]
```

**עקרונות חשובים:**
1. כתוב בעברית תקנית וברורה
2. תרחישים צריכים להיות מציאותיים ומבוססים על איומים אמיתיים
3. שלבי התגובה חייבים להיות ספציפיים ומעשיים
4. הקפד על הפורמט המדויק עם כל השדות
5. השתמש באימוג'ים המתאימים (📋 🎯 🔫 😷 🎥)
6. רמות מורכבות/סיכון/סבירות תמיד באחת מהאפשרויות המפורטות
7. תשובות Yes/No באנגלית בלבד"""

        try:
            with self.writer_client.messages.stream(
                model=config_trinity.WRITER_MODEL_NAME,
                max_tokens=4096,
                temperature=0.8,  # Creative but consistent
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Failed to generate scenario stream: {e}")

    def audit_scenario(self, text: str) -> str:
        """
        Audit and evaluate a scenario using the Judge (Gemini).

        Provides professional quality control and validation of security scenarios.

        Args:
            text: The scenario text to audit (in markdown format)

        Returns:
            Detailed audit results with ratings and recommendations

        Raises:
            RuntimeError: If judge client is not initialized
        """
        if not self.judge_client:
            raise RuntimeError("Judge (Gemini) client not initialized. Check GOOGLE_API_KEY.")

        audit_prompt = f"""אתה מבקר מקצועי (auditor) לתרחישי אבטחה בתחבורה ציבורית.

תפקידך: לבדוק ולהעריך את איכות התרחיש הבא ולתת משוב בונה.

**קריטריונים לבדיקה:**

1. **עמידה בפורמט** (0-10): האם כל השדות הנדרשים קיימים ותקינים?
2. **מציאותיות** (0-10): האם התרחיש סביר ומבוסס על איומים אמיתיים?
3. **בהירות** (0-10): האם התיאור ברור ומובן לצוות אבטחה?
4. **מעשיות** (0-10): האם שלבי התגובה ספציפיים וניתנים ליישום?
5. **שלמות** (0-10): האם כל המידע הדרוש לטיפול באירוע קיים?

**תרחיש לביקורת:**

{text}

---

**הוראות לביקורת:**
- דרג כל קריטריון (0-10)
- תן ציון כולל (ממוצע)
- ציין נקודות חוזק
- ציין נקודות לשיפור
- המלץ על תיקונים ספציפיים אם נדרש
- כתוב בעברית תקנית וברורה"""

        try:
            response = self.judge_client.generate_content(audit_prompt)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Failed to audit scenario: {e}")

    def chat_simulation_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """
        Run a chat simulation using the Simulator (Local Llama) with streaming.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Yields:
            Text chunks as they are generated

        Raises:
            RuntimeError: If simulator client is not initialized
        """
        if not self.simulator_client:
            raise RuntimeError("Simulator (Local) client not initialized. Check LOCAL_BASE_URL.")

        try:
            stream = self.simulator_client.chat.completions.create(
                model=config_trinity.LOCAL_MODEL_NAME,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"Failed to run chat simulation: {e}")
