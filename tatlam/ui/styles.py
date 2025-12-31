"""
tatlam/ui/styles.py - Premium CSS styles for Streamlit UI.

This module provides comprehensive CSS styling for the Tatlam Trinity interface,
including RTL support, dark theme, glassmorphism effects, and animations.
"""


def get_base_theme() -> str:
    """Get base RTL and typography styles."""
    return """
    <style>
    /* ============================================
       IMPORTS & FONTS
       ============================================ */
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&display=swap');

    /* ============================================
       CSS VARIABLES
       ============================================ */
    :root {
        --primary: #818cf8;
        --primary-light: #a5b4fc;
        --primary-dark: #6366f1;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
        --bg-hover: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --success: #22c55e;
        --warning: #f59e0b;
        --error: #ef4444;
        --info: #3b82f6;
        --border-radius: 12px;
        --border-color: rgba(255, 255, 255, 0.1);
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ============================================
       GLOBAL RTL & TYPOGRAPHY
       ============================================ */
    .stApp {
        direction: rtl;
        text-align: right;
        font-family: 'Rubik', 'Segoe UI', Tahoma, sans-serif !important;
    }

    /* All text elements */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'Rubik', 'Segoe UI', Tahoma, sans-serif !important;
    }

    /* Headers */
    h1, h2, h3 {
        text-align: right;
        font-weight: 600;
        letter-spacing: -0.025em;
    }

    h1 {
        font-size: 2.25rem;
        background: linear-gradient(135deg, var(--primary-light), var(--primary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ============================================
       SIDEBAR
       ============================================ */
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
        background: linear-gradient(180deg, var(--bg-dark) 0%, #1e1e2e 100%);
        border-left: 1px solid var(--border-color);
    }

    [data-testid="stSidebar"] .stRadio > label {
        display: flex;
        flex-direction: row-reverse;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        border-radius: var(--border-radius);
        transition: var(--transition);
        margin-bottom: 0.25rem;
    }

    [data-testid="stSidebar"] .stRadio > label:hover {
        background: var(--bg-hover);
    }

    /* ============================================
       INPUT FIELDS
       ============================================ */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox select {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Rubik', sans-serif !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius) !important;
        color: var(--text-primary) !important;
        transition: var(--transition);
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2) !important;
    }

    /* Placeholder text */
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: var(--text-muted) !important;
        text-align: right;
    }

    /* ============================================
       BUTTONS
       ============================================ */
    .stButton > button {
        font-family: 'Rubik', sans-serif !important;
        font-weight: 500;
        border-radius: var(--border-radius) !important;
        transition: var(--transition);
        border: none !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary-dark), var(--primary)) !important;
        box-shadow: var(--shadow-md);
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }

    .stButton > button[kind="secondary"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--bg-hover) !important;
    }

    /* ============================================
       METRICS
       ============================================ */
    [data-testid="stMetricValue"] {
        direction: ltr;
        text-align: right;
        font-weight: 700;
        font-size: 2rem;
        color: var(--text-primary);
    }

    [data-testid="stMetricLabel"] {
        text-align: right;
        color: var(--text-secondary);
        font-weight: 500;
    }

    [data-testid="stMetricDelta"] {
        direction: ltr;
    }
    </style>
    """


def get_glassmorphism_cards() -> str:
    """Get glassmorphism card styles."""
    return """
    <style>
    /* ============================================
       GLASSMORPHISM CARDS
       ============================================ */
    [data-testid="stVerticalBlock"] > div:has(> div.element-container) {
        border-radius: var(--border-radius);
    }

    /* Container with border */
    .stContainer, [data-testid="stContainer"] {
        background: rgba(30, 41, 59, 0.6) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius) !important;
        transition: var(--transition);
    }

    /* Hover effect on cards */
    [data-testid="stContainer"]:hover {
        border-color: rgba(129, 140, 248, 0.3) !important;
        box-shadow: 0 8px 32px rgba(129, 140, 248, 0.1);
    }

    /* Info/Success/Warning/Error boxes */
    .stAlert {
        background: rgba(30, 41, 59, 0.8) !important;
        backdrop-filter: blur(10px);
        border-radius: var(--border-radius) !important;
        border: 1px solid var(--border-color) !important;
    }

    .stAlert[data-baseweb="notification"] {
        direction: rtl;
        text-align: right;
    }

    /* Success alert */
    [data-testid="stAlert"][data-type="success"] {
        border-right: 4px solid var(--success) !important;
        border-left: none !important;
    }

    /* Warning alert */
    [data-testid="stAlert"][data-type="warning"] {
        border-right: 4px solid var(--warning) !important;
        border-left: none !important;
    }

    /* Error alert */
    [data-testid="stAlert"][data-type="error"] {
        border-right: 4px solid var(--error) !important;
        border-left: none !important;
    }

    /* Info alert */
    [data-testid="stAlert"][data-type="info"] {
        border-right: 4px solid var(--info) !important;
        border-left: none !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border-radius: var(--border-radius) !important;
        font-weight: 500;
    }

    .streamlit-expanderContent {
        background: rgba(30, 41, 59, 0.5) !important;
        border-radius: 0 0 var(--border-radius) var(--border-radius) !important;
    }
    </style>
    """


def get_chat_styles() -> str:
    """Get chat message styles."""
    return """
    <style>
    /* ============================================
       CHAT MESSAGES
       ============================================ */
    [data-testid="stChatMessage"] {
        direction: rtl;
        text-align: right;
        background: rgba(30, 41, 59, 0.5) !important;
        backdrop-filter: blur(8px);
        border-radius: var(--border-radius) !important;
        border: 1px solid var(--border-color) !important;
        padding: 1rem !important;
        margin-bottom: 0.75rem !important;
    }

    /* User messages */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: rgba(99, 102, 241, 0.15) !important;
        border-color: rgba(129, 140, 248, 0.3) !important;
    }

    /* Assistant messages */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: rgba(30, 41, 59, 0.7) !important;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        direction: rtl;
    }

    [data-testid="stChatInput"] textarea {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Rubik', sans-serif !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        text-align: right;
    }
    </style>
    """


def get_animations() -> str:
    """Get animation styles."""
    return """
    <style>
    /* ============================================
       ANIMATIONS
       ============================================ */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }

    @keyframes shimmer {
        0% {
            background-position: -200% center;
        }
        100% {
            background-position: 200% center;
        }
    }

    /* Apply fade-in animation to main content */
    [data-testid="stVerticalBlock"] > div {
        animation: fadeInUp 0.4s ease-out;
    }

    /* Stagger animation for cards */
    [data-testid="stVerticalBlock"] > div:nth-child(1) { animation-delay: 0.05s; }
    [data-testid="stVerticalBlock"] > div:nth-child(2) { animation-delay: 0.1s; }
    [data-testid="stVerticalBlock"] > div:nth-child(3) { animation-delay: 0.15s; }
    [data-testid="stVerticalBlock"] > div:nth-child(4) { animation-delay: 0.2s; }

    /* Loading skeleton pulse */
    .skeleton {
        background: linear-gradient(90deg, var(--bg-card), var(--bg-hover), var(--bg-card));
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: var(--border-radius);
    }

    /* Spinner enhancement */
    .stSpinner > div {
        border-color: var(--primary) transparent transparent transparent !important;
    }
    </style>
    """


def get_status_indicators() -> str:
    """Get status indicator styles (LED dots)."""
    return """
    <style>
    /* ============================================
       STATUS INDICATORS
       ============================================ */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-left: 8px;
    }

    .status-dot.online {
        background: var(--success);
        box-shadow: 0 0 8px var(--success);
        animation: pulse 2s infinite;
    }

    .status-dot.offline {
        background: var(--error);
        box-shadow: 0 0 8px var(--error);
    }

    .status-dot.warning {
        background: var(--warning);
        box-shadow: 0 0 8px var(--warning);
    }

    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .status-badge.success {
        background: rgba(34, 197, 94, 0.15);
        color: var(--success);
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .status-badge.error {
        background: rgba(239, 68, 68, 0.15);
        color: var(--error);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    </style>
    """


def get_catalog_cards() -> str:
    """Get catalog card specific styles."""
    return """
    <style>
    /* ============================================
       CATALOG CARDS
       ============================================ */
    .scenario-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        padding: 1.25rem;
        transition: var(--transition);
        cursor: pointer;
    }

    .scenario-card:hover {
        transform: translateY(-4px);
        border-color: var(--primary);
        box-shadow: 0 12px 24px rgba(129, 140, 248, 0.15);
    }

    .scenario-card .title {
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
    }

    .scenario-card .meta {
        color: var(--text-secondary);
        font-size: 0.875rem;
    }

    /* Category tags */
    .category-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        background: rgba(129, 140, 248, 0.15);
        color: var(--primary-light);
        border: 1px solid rgba(129, 140, 248, 0.3);
    }

    /* Threat level tags */
    .threat-low {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border-color: rgba(34, 197, 94, 0.3);
    }

    .threat-medium {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border-color: rgba(245, 158, 11, 0.3);
    }

    .threat-high {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border-color: rgba(239, 68, 68, 0.3);
    }
    </style>
    """


def get_accessibility() -> str:
    """Get accessibility-focused styles."""
    return """
    <style>
    /* ============================================
       ACCESSIBILITY
       ============================================ */
    /* Focus states */
    *:focus-visible {
        outline: 2px solid var(--primary) !important;
        outline-offset: 2px !important;
    }

    /* Skip to content (screen reader) */
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }

    /* High contrast text */
    .high-contrast {
        color: #ffffff !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }

    /* Reduced motion */
    @media (prefers-reduced-motion: reduce) {
        *,
        *::before,
        *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>
    """


def get_full_stylesheet() -> str:
    """
    Get the complete stylesheet combining all style modules.

    Returns:
        str: Complete CSS stylesheet as HTML style tags.
    """
    return (
        get_base_theme()
        + get_glassmorphism_cards()
        + get_chat_styles()
        + get_animations()
        + get_status_indicators()
        + get_catalog_cards()
        + get_accessibility()
    )
