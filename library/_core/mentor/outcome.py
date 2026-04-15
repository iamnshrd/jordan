"""Richer outcome inference for mentor replies."""

from __future__ import annotations


def classify_reply(question: str, route: str = '') -> str:
    q = (question or '').lower()
    movement_markers = ['сделал', 'сделала', 'написал', 'написала', 'поговорил', 'поговорила', 'начал', 'начала', 'получилось', 'закрыл', 'закрыла']
    reflection_markers = ['понял, что', 'вижу, что', 'осознал', 'похоже, что', 'я избегаю', 'я понял']
    theater_markers = ['надо бы', 'было бы неплохо', 'думаю сделать', 'собираюсь как-нибудь', 'в целом понял что делать']
    truthful_delay_markers = ['сделаю завтра в', 'сегодня после', 'после работы', 'после созвона', 'после встречи', 'как закончу', 'в ', 'завтра утром']
    manipulative_fragility_markers = ['не дави', 'слишком жестко', 'ты давишь', 'мне неприятно это слышать']
    defensive_intelligence_markers = ['это сложнее', 'тут много факторов', 'это не так однозначно', 'нельзя так упрощать', 'все немного сложнее']

    if any(x in q for x in ['отстань', 'заеб', 'бесишь', 'не лезь']):
        return 'irritation'
    if any(x in q for x in manipulative_fragility_markers) and any(x in q for x in ['не хочу', 'не буду', 'не могу', 'не сейчас']):
        return 'manipulative-fragility'
    if any(x in q for x in ['разваливаюсь', 'не вывожу', 'очень тяжело', 'мне плохо', 'не могу сейчас']) and route in {'shame-self-contempt', 'addiction-chaos'}:
        return 'fragility'
    if any(x in q for x in ['яснее вижу, к чему иду', 'понял, куда иду', 'понял, к чему это ведет', 'стал яснее мой ориентир']):
        return 'ends-clarified'
    if any(x in q for x in ['теперь яснее, где я вру себе', 'вижу свою рационализацию', 'это было просто оправдание', 'я прикрывался объяснением']):
        return 'rationalization-exposed'
    if any(x in q for x in ['понял, что мне не хватает дисциплины', 'это вопрос привычки', 'я сам строю эту привычку', 'я повторением делаю это нормой']):
        return 'habit-recognition'
    if any(x in q for x in ['здесь мне не хватило мужества', 'здесь мне не хватило меры', 'здесь мне не хватило благоразумия', 'я был несправедлив']):
        return 'virtue-recognition'
    if any(x in q for x in ['теперь лучше понимаю, в чем ошибка моего мышления', 'я путал важное и второстепенное', 'я плохо рассуждал', 'я неправильно ставил рамку']):
        return 'judgment-clarified'
    if any(x in q for x in ['я просто красиво говорю', 'я опять делаю вид, что двигаюсь', 'это был только красивый ответ', 'я изображаю прогресс']):
        return 'moral-posturing'
    if any(x in q for x in theater_markers) and not any(x in q for x in movement_markers):
        return 'compliance-theater'
    if any(x in q for x in truthful_delay_markers) and not any(x in q for x in movement_markers):
        return 'truthful-delay'
    if any(x in q for x in ['не хочу', 'не буду', 'потом', 'не сейчас']):
        if any(x in q for x in truthful_delay_markers):
            return 'truthful-delay'
        if any(x in q for x in ['завтра', 'вечером', 'сегодня вечером', 'позже сегодня']):
            return 'delay-with-intent'
        return 'lazy-delay'
    if any(x in q for x in movement_markers):
        if any(x in q for x in ['чуть', 'немного', 'маленький', 'слегка']):
            return 'movement-small'
        if any(x in q for x in ['но это скорее для вида', 'чисто чтобы отвязаться', 'скорее формально', 'для галочки']):
            return 'movement-theater'
        return 'movement'
    if any(x in q for x in ['немного продвинулся', 'чуть сдвинул', 'маленький шаг', 'слегка продвинулся']):
        return 'movement-small'
    if any(x in q for x in defensive_intelligence_markers) and not any(x in q for x in movement_markers):
        return 'defensive-intelligence'
    if any(x in q for x in reflection_markers) and not any(x in q for x in movement_markers):
        if any(x in q for x in ['завтра', 'сегодня', 'сейчас сделаю', 'следующий шаг']):
            return 'reflection-with-intent'
        return 'reflection'
    if any(x in q for x in ['ок', 'понял', 'ага', 'ясно', 'хорошо']) and not any(x in q for x in movement_markers):
        return 'compliance'
    if any(x in q for x in ['кстати', 'вообще', 'ладно, но', 'не об этом']) and not any(x in q for x in movement_markers + reflection_markers):
        return 'deflection'
    return 'neutral'
