#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library._core.mentor.outcome import classify_reply

CASES = [
    ('Да, я написал ему и закрыл этот разговор', 'relationship-maintenance', 'movement'),
    ('Я немного продвинулся и чуть сдвинул это', 'career-vocation', 'movement-small'),
    ('Я понял, что избегаю этого разговора', 'relationship-maintenance', 'reflection'),
    ('Я понял, что избегаю этого разговора, и завтра напишу ему', 'relationship-maintenance', 'reflection-with-intent'),
    ('Ок, понял', 'career-vocation', 'compliance'),
    ('Потом, не сейчас', 'career-vocation', 'lazy-delay'),
    ('Не сейчас, вечером разберу это', 'career-vocation', 'delay-with-intent'),
    ('Сделаю завтра утром после созвона', 'career-vocation', 'truthful-delay'),
    ('Надо бы этим заняться, в целом понял что делать', 'career-vocation', 'compliance-theater'),
    ('Да, сделал, но скорее для галочки', 'career-vocation', 'movement-theater'),
    ('Не дави, мне неприятно это слышать, я не хочу сейчас', 'shame-self-contempt', 'manipulative-fragility'),
    ('Это не так однозначно, тут много факторов', 'self-deception', 'defensive-intelligence'),
    ('Отстань уже', 'career-vocation', 'irritation'),
    ('Мне сейчас очень тяжело, я не вывожу', 'shame-self-contempt', 'fragility'),
    ('Теперь лучше понимаю, в чем ошибка моего мышления', 'self-deception', 'judgment-clarified'),
    ('Яснее вижу, к чему иду', 'career-vocation', 'ends-clarified'),
    ('Это было просто оправдание, я прикрывался объяснением', 'self-deception', 'rationalization-exposed'),
    ('Я сам строю эту привычку повторением', 'addiction-chaos', 'habit-recognition'),
    ('Здесь мне не хватило мужества', 'relationship-maintenance', 'virtue-recognition'),
    ('Я опять делаю вид, что двигаюсь, это был только красивый ответ', 'resentment', 'moral-posturing'),
]


def main() -> None:
    results = []
    passed = 0
    for text, route, expected in CASES:
        got = classify_reply(text, route=route)
        ok = got == expected
        results.append({'text': text, 'route': route, 'expected': expected, 'got': got, 'pass': ok})
        passed += int(ok)
    emit_report(results)


if __name__ == '__main__':
    main()
