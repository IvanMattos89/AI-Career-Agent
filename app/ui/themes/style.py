"""Tokens e estilo global da interface do AI Career Agent."""

PRIMARY = "#2563EB"
PRIMARY_HOVER = "#1D4ED8"
PRIMARY_SOFT = "#EFF6FF"
SUCCESS = "#16A34A"
WARNING = "#D97706"
ATTENTION = "#EA580C"
DANGER = "#DC2626"

BACKGROUND = "#F6F8FC"
CARD_BACKGROUND = "#FFFFFF"
BORDER = "#E2E8F0"
SIDEBAR = "#0F172A"
SIDEBAR_HOVER = "#1E293B"

TEXT = "#0F172A"
TEXT_SECONDARY = "#64748B"

CARD_RADIUS = 14
CARD_PADDING = 18
TITLE_SIZE = 28
SUBTITLE_SIZE = 16
TEXT_SIZE = 13
SPACING = 12
MARGIN = 20


def application_stylesheet():
    """Folha de estilo compartilhada por todas as páginas e diálogos."""
    return f"""
    QMainWindow, QWidget#appRoot {{
        background: {BACKGROUND};
    }}
    QWidget {{
        color: {TEXT};
        font-family: "Segoe UI";
        font-size: 13px;
    }}
    QLabel#pageTitle {{ color: {TEXT}; font-size: 28px; font-weight: 750; }}
    QLabel#pageSubtitle {{ color: {TEXT_SECONDARY}; font-size: 13px; }}
    QLabel#sectionTitle {{ color: {TEXT}; font-size: 17px; font-weight: 700; }}
    QLabel#profileBanner {{
        background: {PRIMARY_SOFT}; color: #1E3A8A; border: 1px solid #BFDBFE;
        border-radius: 12px; padding: 14px;
    }}
    QLabel#mutedText {{ color: {TEXT_SECONDARY}; }}
    QLabel#settingsFeedback {{
        background: #F8FAFC; color: {TEXT_SECONDARY}; border: 1px solid {BORDER};
        border-radius: 10px; padding: 11px 14px;
    }}
    QLabel#settingsFeedback[state="success"] {{ background: #F0FDF4; color: #166534; border-color: #BBF7D0; }}
    QLabel#settingsFeedback[state="error"] {{ background: #FEF2F2; color: #991B1B; border-color: #FECACA; }}
    QLabel#settingsSummary {{
        background: {PRIMARY_SOFT}; color: #1E3A8A; border: 1px solid #BFDBFE;
        border-radius: 12px; padding: 14px;
    }}
    QLabel#serviceStatus {{ border-radius: 9px; padding: 8px 12px; background: #F1F5F9; color: {TEXT_SECONDARY}; }}
    QLabel#serviceStatus[state="success"] {{ background: #DCFCE7; color: #166534; }}
    QLabel#serviceStatus[state="warning"] {{ background: #FFF7ED; color: #9A3412; }}
    QLabel#serviceStatus[state="error"] {{ background: #FEE2E2; color: #991B1B; }}
    QFrame#settingsMetric {{
        background: {CARD_BACKGROUND}; border: 1px solid {BORDER};
        border-radius: 12px; min-height: 84px;
    }}
    QFrame#settingsMetric QLabel {{ border: none; background: transparent; }}
    QLabel#metricLabel {{ color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600; }}
    QLabel#metricValue {{ color: {TEXT}; font-size: 20px; font-weight: 750; }}
    QLabel#privacyNotice {{
        background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A;
        border-radius: 10px; padding: 13px;
    }}
    QScrollArea, QStackedWidget {{
        background: transparent;
        border: none;
    }}
    QToolTip {{
        color: {TEXT};
        background: {CARD_BACKGROUND};
        border: 1px solid {BORDER};
        padding: 7px;
    }}
    QPushButton {{
        min-height: 36px;
        padding: 0 15px;
        border: 1px solid {PRIMARY};
        border-radius: 9px;
        background: {PRIMARY};
        color: white;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER}; }}
    QPushButton:pressed {{ background: #1E40AF; }}
    QPushButton:disabled {{ background: #E2E8F0; border-color: #E2E8F0; color: #94A3B8; }}
    QPushButton[secondary="true"] {{
        background: {CARD_BACKGROUND};
        color: {TEXT};
        border-color: {BORDER};
    }}
    QPushButton[secondary="true"]:hover {{ background: #F8FAFC; border-color: #CBD5E1; }}
    QPushButton[danger="true"] {{ background: white; color: {DANGER}; border-color: #FECACA; }}
    QPushButton[danger="true"]:hover {{ background: #FEF2F2; border-color: {DANGER}; }}
    QWidget#sidebar {{ background: {SIDEBAR}; }}
    QLabel#brandTitle {{ color: white; font-size: 17px; font-weight: 700; }}
    QLabel#brandVersion {{ color: #94A3B8; font-size: 11px; }}
    QLabel#brandBadge {{
        color: white; background: {PRIMARY}; border-radius: 10px;
        font-size: 15px; font-weight: 800; padding: 8px;
    }}
    QLabel#sidebarFooter {{ color: #94A3B8; font-size: 11px; }}
    QPushButton[nav="true"] {{
        min-height: 44px; padding: 0 14px; border: none; border-radius: 9px;
        background: transparent; color: #CBD5E1; text-align: left; font-weight: 500;
    }}
    QPushButton[nav="true"]:hover {{ background: {SIDEBAR_HOVER}; color: white; }}
    QPushButton[nav="true"]:checked {{ background: {PRIMARY}; color: white; font-weight: 700; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        min-height: 36px; padding: 0 11px; background: {CARD_BACKGROUND};
        color: {TEXT}; border: 1px solid {BORDER}; border-radius: 9px;
        selection-background-color: {PRIMARY};
    }}
    QTextEdit, QPlainTextEdit {{ padding: 10px; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {PRIMARY};
    }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QGroupBox {{
        margin-top: 14px; padding: 18px 14px 14px; background: {CARD_BACKGROUND};
        border: 1px solid {BORDER}; border-radius: {CARD_RADIUS}px; font-weight: 700;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: {TEXT}; }}
    QTableWidget {{
        background: {CARD_BACKGROUND}; alternate-background-color: #F8FAFC;
        border: 1px solid {BORDER}; border-radius: 10px; gridline-color: {BORDER};
        selection-background-color: #DBEAFE; selection-color: {TEXT};
    }}
    QHeaderView::section {{
        background: #F8FAFC; color: {TEXT_SECONDARY}; padding: 10px;
        border: none; border-bottom: 1px solid {BORDER}; font-weight: 700;
    }}
    QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 10px; background: {CARD_BACKGROUND}; top: -1px; }}
    QTabBar::tab {{
        background: transparent; color: {TEXT_SECONDARY}; padding: 10px 16px;
        border-bottom: 2px solid transparent; font-weight: 600;
    }}
    QTabBar::tab:selected {{ color: {PRIMARY}; border-bottom-color: {PRIMARY}; }}
    QProgressBar {{
        min-height: 12px; max-height: 12px; border: none; border-radius: 6px;
        background: #E2E8F0; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{ border-radius: 6px; background: {PRIMARY}; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #CBD5E1; min-height: 30px; border-radius: 5px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
