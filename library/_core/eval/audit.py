from library._core.runtime.frame import select_frame
from library.config import RUNTIME_AUDIT_REPORT
from library.utils import save_json

QUESTIONS = [
    'Я не понимаю, куда мне двигаться в карьере и что вообще для меня призвание',
    'У нас с женой постоянные конфликты и скрытая обида',
    'Мне стыдно за себя и я чувствую отвращение к себе',
    'Я потерял смысл, дисциплину и направление',
    'Моя жизнь превращается в хаос, я всё больше спиваюсь и теряю контроль',
]

def audit():
    """Run audit over fixed questions. Returns report dict."""
    rows = []
    for q in QUESTIONS:
        data = select_frame(q)
        rows.append({
            'question': q,
            'preferred_sources': data.get('preferred_sources'),
            'theme': (data.get('selected_theme') or {}).get('name'),
            'principle': (data.get('selected_principle') or {}).get('name'),
            'pattern': (data.get('selected_pattern') or {}).get('name'),
            'confidence': data.get('confidence'),
        })
    report = {'cases': rows}
    save_json(RUNTIME_AUDIT_REPORT, report)
    return report
