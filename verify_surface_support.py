
import sys
import logging
from tatlam.core.prompts import PromptManager
from tatlam.core.doctrine import get_system_prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_doctrine_injection():
    logger.info("Testing Doctrine Injection...")
    
    # Test Allenby (Default)
    allenby_prompt = get_system_prompt("writer", venue="allenby")
    assert "תחנת אלנבי" in allenby_prompt or "Allenby" in allenby_prompt or "פרק 2: זירת הפעולה" in allenby_prompt
    assert "ציר יפו" not in allenby_prompt
    logger.info("✅ Allenby Doctrine OK")
    
    # Test Jaffa (Surface)
    jaffa_prompt = get_system_prompt("writer", venue="jaffa")
    assert "ציר יפו" in jaffa_prompt
    assert "Surface Station" in jaffa_prompt or "עילי" in jaffa_prompt
    assert "אין שערים" in jaffa_prompt
    logger.info("✅ Jaffa Doctrine OK")

def test_prompt_manager_detection():
    logger.info("Testing PromptManager Detection...")
    pm = PromptManager()
    
    # Test Explicit Category
    jaffa_input = "יצירת תרחיש ירי"
    prompt = pm.format_scenario_prompt(jaffa_input, category="tachanot-iliyot")
    assert "Jaffa Line" in prompt
    assert "תורת ההפעלה - ציר יפו" in prompt
    logger.info("✅ Category Detection OK")
    
    # Test Keyword Detection
    keyword_input = "תרחיש בתחנה עילית"
    prompt = pm.format_scenario_prompt(keyword_input)
    assert "Jaffa Line" in prompt
    logger.info("✅ Keyword Detection OK")
    
    # Test Default
    default_input = "תרחיש חפץ חשוד"
    prompt = pm.format_scenario_prompt(default_input)
    assert "Allenby" in prompt
    assert "Jaffa Line" not in prompt
    logger.info("✅ Default Behavior OK")

if __name__ == "__main__":
    try:
        test_doctrine_injection()
        test_prompt_manager_detection()
        print("\n🎉 ALL CHECKS PASSED: Surface Station Support is Active!")
    except AssertionError as e:
        print(f"\n❌ CHECK FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
