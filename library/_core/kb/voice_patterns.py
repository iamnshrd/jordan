#!/usr/bin/env python3
"""Extract transcript-derived clarify/voice utility into a DB-backed layer."""
from __future__ import annotations

from collections import Counter
import json
import re

from library.config import friendly_source_name
from library.db import connect


TARGET_SOURCE_NAMES = {
    'master-relationships',
    'romantic-relationship',
    'would-you-love-the-same-man',
    'evolution-sex-and-desire-david-buss-ep-235',
    'w-lex',
}


VOICE_PATTERN_RULES = [
    {
        'move_name': 'support-the-mother-under-strain',
        'pattern_type': 'clarify_voice',
        'theme_name': 'parenting/boundaries',
        'profile_hint': 'parenting-boundaries',
        'pattern_text': (
            'В первые тяжёлые периоды семьи вопрос часто не в справедливом '
            'подсчёте усилий, а в том, кто удерживает под давлением саму '
            'связь между матерью, ребёнком и домом.'
        ),
        'tags': ['parenting', 'support', 'clarify'],
        'score': 8,
        'note': 'Use when parenting or family strain needs to be reframed as support under load.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'primary role of the father',
            r'support the mother',
            r'intense care of the infant',
        ],
    },
    {
        'move_name': 'beneath-trigger',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Если реакция явно сильнее повода, ищи не повод, а лежащий под ним '
            'неразрешённый конфликт, обиду или след старого предательства.'
        ),
        'tags': ['relationship', 'surface-to-depth', 'clarify'],
        'score': 10,
        'note': 'Use for clarifies that move from surface complaint to hidden conflict.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'disproportionate to the trigger',
            r"there'?s something underneath",
            r'how far underneath',
        ],
    },
    {
        'move_name': 'not-about-winning',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'resentment-and-silence',
        'pattern_text': (
            'В близком конфликте цель не выиграть спор, а прояснить правду и '
            'сохранить сам союз.'
        ),
        'tags': ['relationship', 'conflict', 'clarify'],
        'score': 10,
        'note': 'Useful for resentment/silence clarifies.',
        'source_names': {'master-relationships'},
        'patterns': [
            r"you don'?t win an argument with your wife",
            r"the aim should be.*not let'?s win",
            r"let'?s solve this",
        ],
    },
    {
        'move_name': 'humility-before-pride',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'resentment-and-silence',
        'pattern_text': (
            'Даже если твоя доля вины мала, полезнее начать с неё: это открывает '
            'возможность чему-то научиться, вместо того чтобы застрять в pride.'
        ),
        'tags': ['relationship', 'humility', 'clarify'],
        'score': 9,
        'note': 'Use when clarify should push toward self-examination rather than accusation.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'humility rather than pride',
            r'you might have something to learn',
            r'even if it[\' ]?s only 5% me',
        ],
    },
    {
        'move_name': 'ghosts-of-the-past-cloud-the-path',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Пока человек не разобрался с призраками прошлого, они будут '
            'затуманивать новый путь и портить даже честные попытки двинуться '
            'вперёд.'
        ),
        'tags': ['meaning', 'past', 'clarify'],
        'score': 8,
        'note': 'Use when old material still contaminates direction and clarity.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'ghosts of the past',
            r'new path forward with clarity',
            r'demons of the past',
        ],
    },
    {
        'move_name': 'memory-needs-a-moral',
        'pattern_type': 'clarify_voice',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Память полезна не сама по себе, а тогда, когда из неё извлечён '
            'правильный моральный вывод, который меняет будущие решения.'
        ),
        'tags': ['memory', 'truth', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should ask what lesson has not yet been drawn.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'you do not remember the past',
            r'derived the appropriate moral',
            r'duplicate what was good about it in the future',
        ],
    },
    {
        'move_name': 'self-deception-is-truth-without-order',
        'pattern_type': 'framing_move',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Самообман часто выглядит не как отсутствие правды, а как отказ строить '
            'вокруг уже известной правды реальный порядок.'
        ),
        'tags': ['truth', 'framing', 'self-deception'],
        'score': 8,
        'note': 'Frame self-deception as failure to organize around known truth.',
        'source_names': {'master-relationships', 'w-lex'},
        'patterns': [
            r'derived the appropriate moral',
            r'can[\' ]?t distinguish between truth and falsehood',
            r'truth is the deity',
        ],
    },
    {
        'move_name': 'narrow-self-deception-to-one-lie',
        'pattern_type': 'narrowing_question',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Не расплывайся. Назови одну ложь, вокруг которой ты всё ещё строишь свой день.'
        ),
        'tags': ['truth', 'question', 'self-deception'],
        'score': 7,
        'note': 'Narrow self-deception to one active lie.',
        'source_names': {'master-relationships', 'w-lex'},
        'patterns': [
            r'derived the appropriate moral',
            r'truth is the deity',
            r'making the outcome your deity',
        ],
    },
    {
        'move_name': 'difference-becomes-chronic-conflict',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Если между людьми слишком большой и устойчивый разрыв в базовых '
            'темпераментных вещах, различие быстро становится хроническим '
            'источником конфликта.'
        ),
        'tags': ['relationship', 'difference', 'clarify'],
        'score': 9,
        'note': 'Use when clarify should name enduring mismatch instead of one-off incident.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'too much mismatch',
            r'chronic source of conflict',
            r'too different in your',
        ],
    },
    {
        'move_name': 'complementarity-beats-identicality',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Пара не обязана состоять из одинаковых людей; чаще вопрос в том, '
            'способны ли различия уравновешивать слабости, а не раздирать союз.'
        ),
        'tags': ['relationship', 'balance', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should frame difference as balance rather than mirror-sameness.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'don[\' ]?t know what the optimal',
            r'don[\' ]?t want to live with someone who[\' ]?s exactly like you',
            r'balance each other out',
        ],
    },
    {
        'move_name': 'remember-love-before-conflict',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Перед трудным разговором полезно помнить, зачем ты вообще защищаешь '
            'эту связь; иначе спор быстро подменяет саму причину, по которой вы '
            'вместе.'
        ),
        'tags': ['relationship', 'bond', 'clarify'],
        'score': 8,
        'note': 'Use for clarifies where the hidden issue is erosion of bond/trust.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'remember that you love',
            r'practice gratitude',
            r'you have to remember that you love the person',
        ],
    },
    {
        'move_name': 'marriage-is-constructive-wrestling',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'В хорошей связи другой человек нужен не только для комфорта, но и '
            'как тот, с кем ты вынужден бороться за правду и за собственное '
            'взросление.'
        ),
        'tags': ['relationship', 'growth', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should frame conflict as growth-producing contention.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'you want someone to contend with you',
            r'you learn through that wrestling',
            r'that\'s the spiritual aspect of marriage',
        ],
    },
    {
        'move_name': 'state-your-limit-plainly',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'desire-mismatch',
        'pattern_text': (
            'Пределы и нужду нужно называть прямо, пока раздражение не стало '
            'resentment.'
        ),
        'tags': ['relationship', 'communication', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should move toward naming needs or overload.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'i need help right now',
            r'talk to your partner',
            r'if you notice that you[\' ]?re irritable and resentful',
        ],
    },
    {
        'move_name': 'stable-family-needs-divided-labor',
        'pattern_type': 'clarify_voice',
        'theme_name': 'parenting/boundaries',
        'profile_hint': 'parenting-boundaries',
        'pattern_text': (
            'Семейная устойчивость держится не на абстрактной любви, а на '
            'реальном разделении труда и на признании того, кто именно сейчас '
            'перегружен.'
        ),
        'tags': ['parenting', 'family', 'clarify'],
        'score': 8,
        'note': 'Useful when parenting or relationship strain is really a labor/allocation problem.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'need to divide up the labor',
            r'woman is completely overwhelmed',
            r'need a stable basis for children',
        ],
    },
    {
        'move_name': 'commitment-tangles-lives-together',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Связь становится реальной тогда, когда люди не просто рядом, а '
            'действительно сплетают свои жизни и делают друг друга частью '
            'долгого порядка.'
        ),
        'tags': ['relationship', 'commitment', 'clarify'],
        'score': 6,
        'note': 'Use when clarify should frame commitment as entwined lives, not casual companionship.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'tangle your life together',
            r'relationships are trustworthy',
        ],
    },
    {
        'move_name': 'sanity-needs-social-correction',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Часть внутренней собранности держится не в голове, а в живой '
            'обратной связи с другими людьми; без неё человек быстро съезжает в '
            'дрейф и самозаблуждение.'
        ),
        'tags': ['meaning', 'correction', 'clarify'],
        'score': 8,
        'note': 'Useful when aimlessness is tied to isolation and lack of corrective structure.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'you outsource most of your sanity',
            r'people signal to you',
            r'you go off the rails',
        ],
    },
    {
        'move_name': 'drift-without-structure',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Когда человек остаётся без структуры и внешней корректировки, он '
            'начинает дрейфовать и терять форму.'
        ),
        'tags': ['meaning', 'structure', 'clarify'],
        'score': 10,
        'note': 'Use for aimlessness clarifies.',
        'source_names': {'romantic-relationship'},
        'patterns': [
            r'if you[\' ]?re alone you drift',
            r'surrounded by other people',
            r'people signal to you',
        ],
    },
    {
        'move_name': 'aimlessness-is-drift-not-fog',
        'pattern_type': 'framing_move',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Когда человек чувствует, что потерялся, это часто не туман в абстрактном смысле, '
            'а дрейф без структуры, коррекции и добровольно принятой цели.'
        ),
        'tags': ['meaning', 'framing', 'direction'],
        'score': 9,
        'note': 'Frame aimlessness as drift and lack of aim rather than vague fog.',
        'source_names': {'romantic-relationship', 'w-lex'},
        'patterns': [
            r'if you[\' ]?re alone you drift',
            r'goal confusion anxiety and hopelessness',
            r'as soon as you have a goal a pathway opens up',
        ],
    },
    {
        'move_name': 'narrow-aimlessness-to-what-is-collapsing',
        'pattern_type': 'narrowing_question',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Скажи прямо: что у тебя разваливается первым — дисциплина, цель, '
            'отношения или уважение к себе?'
        ),
        'tags': ['meaning', 'question', 'direction'],
        'score': 8,
        'note': 'Narrow aimlessness to the first failing domain.',
        'source_names': {'romantic-relationship', 'master-relationships', 'w-lex'},
        'patterns': [
            r'if you[\' ]?re alone you drift',
            r'bring your narrative up to date',
            r'as soon as you have a goal a pathway opens up',
        ],
    },
    {
        'move_name': 'unresolved-past-as-pitfall',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'То, что остаётся эмоционально горячим и неразобранным, часто '
            'указывает на яму, в которую человек рискует снова свалиться.'
        ),
        'tags': ['meaning', 'past', 'clarify'],
        'score': 9,
        'note': 'Use when clarify should ask what remains unresolved and active.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'pitfall waiting for you to fall into',
            r'still hot and active',
            r'emotional significance',
        ],
    },
    {
        'move_name': 'bring-your-story-up-to-date',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Пока человек не собрал собственную историю в связную карту смысла, '
            'ему трудно понять, где он находится и куда вообще стоит идти дальше.'
        ),
        'tags': ['meaning', 'narrative', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should ask for the one unresolved chapter that still governs the present.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'bring your narrative up to date',
            r'once you know where you are',
            r'you can plot your future',
        ],
    },
    {
        'move_name': 'higher-investment-raises-the-cost',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'Там, где инвестиция в связь и последствия выше, выбор и тревога '
            'вокруг него тоже становятся тяжелее; это не мелкая деталь, а часть '
            'архитектуры самой проблемы.'
        ),
        'tags': ['relationship', 'investment', 'clarify'],
        'score': 7,
        'note': 'Use for sexuality/intimacy clarifies where asymmetry of cost matters.',
        'source_names': {'would-you-love-the-same-man'},
        'patterns': [
            r'the sex that invests more',
            r'definition of female',
            r'reproduction for human beings doesn[\' ]?t end with sex',
        ],
    },
    {
        'move_name': 'sexual-domain-is-about-investment-risk-and-choice',
        'pattern_type': 'framing_move',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'В таких вопросах дело почти никогда не в одной технике; здесь быстро '
            'встают выбор, вложение, риск, отказ и цена ошибки.'
        ),
        'tags': ['relationship', 'sexuality', 'framing'],
        'score': 9,
        'note': 'Frame sexual-problem asks as pair-bonding and investment problems rather than technique.',
        'source_names': {'would-you-love-the-same-man', 'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'the sex that invests more',
            r'reproduction for human beings doesn[\' ]?t end with sex',
            r'understanding that makes it less harsh',
        ],
    },
    {
        'move_name': 'narrow-sexual-scope-to-one-knot',
        'pattern_type': 'narrowing_question',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'Не разбрасывайся. Назови один узел: желание, стыд, отказ, ревность '
            'или борьбу за власть и близость.'
        ),
        'tags': ['relationship', 'sexuality', 'question'],
        'score': 8,
        'note': 'Narrow a broad sexual-problem ask to one knot.',
        'source_names': {'would-you-love-the-same-man', 'w-lex'},
        'patterns': [
            r'the sex that invests more',
            r'alert to that form of deception as a threat',
            r'goal confusion anxiety and hopelessness',
        ],
    },
    {
        'move_name': 'rejection-threatens-dignity-and-bond',
        'pattern_type': 'framing_move',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'sexual-rejection',
        'pattern_text': (
            'Когда близость снова и снова исчезает, это почти всегда бьёт не только '
            'по телу, но и по достоинству, доверию и ощущению, что тебя по-прежнему выбирают.'
        ),
        'tags': ['relationship', 'sexuality', 'framing'],
        'score': 9,
        'note': 'Frame sexual rejection as a bond and dignity wound, not only a physical absence.',
        'source_names': {'master-relationships', 'would-you-love-the-same-man'},
        'patterns': [
            r'disproportionate to the trigger',
            r'costs are higher',
            r'sold herself short',
        ],
    },
    {
        'move_name': 'narrow-rejection-to-core-pain',
        'pattern_type': 'narrowing_question',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'sexual-rejection',
        'pattern_text': (
            'Скажи без украшений: больнее здесь отвержение, унижение, злость или '
            'страх, что сама связь уже начала размыкаться?'
        ),
        'tags': ['relationship', 'sexuality', 'question'],
        'score': 8,
        'note': 'Narrow sexual rejection to the main pain axis.',
        'source_names': {'master-relationships', 'would-you-love-the-same-man'},
        'patterns': [
            r'disproportionate to the trigger',
            r'alert to that form of deception as a threat',
            r'costs are higher',
        ],
    },
    {
        'move_name': 'mismatch-is-structural-not-technical',
        'pattern_type': 'framing_move',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'desire-mismatch',
        'pattern_text': (
            'Сильное расхождение в желании редко остаётся мелкой нестыковкой; '
            'если оно устойчиво, оно перестраивает весь порядок близости и быта.'
        ),
        'tags': ['relationship', 'sexuality', 'framing'],
        'score': 9,
        'note': 'Frame desire mismatch as structural, not technical.',
        'source_names': {'romantic-relationship', 'master-relationships'},
        'patterns': [
            r'too much mismatch',
            r'chronic source of conflict',
            r'if you notice that you[\' ]?re irritable and resentful',
        ],
    },
    {
        'move_name': 'narrow-mismatch-to-primary-loss',
        'pattern_type': 'narrowing_question',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'desire-mismatch',
        'pattern_text': (
            'Назови одну потерю прямо: ты здесь больше страдаешь от телесного голода, '
            'эмоционального отдаления или от того, что тебя всё время ставят после всего остального?'
        ),
        'tags': ['relationship', 'sexuality', 'question'],
        'score': 8,
        'note': 'Narrow desire mismatch to the main felt loss.',
        'source_names': {'romantic-relationship', 'master-relationships'},
        'patterns': [
            r'too much mismatch',
            r'need to divide up the labor',
            r'if you notice that you[\' ]?re irritable and resentful',
        ],
    },
    {
        'move_name': 'threat-tuning-follows-vulnerability',
        'pattern_type': 'clarify_voice',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Тревога часто растёт не потому, что человек слаб, а потому, что у '
            'него действительно больше того, что можно потерять и что нужно '
            'оберегать.'
        ),
        'tags': ['fear', 'vulnerability', 'clarify'],
        'score': 8,
        'note': 'Useful when fear should be reframed as vigilance under genuine vulnerability.',
        'source_names': {'would-you-love-the-same-man'},
        'patterns': [
            r'women are more attuned to threat',
            r'proxies for the vulnerability of their infant',
            r'over responsive to threat',
        ],
    },
    {
        'move_name': 'manipulation-is-also-a-threat',
        'pattern_type': 'clarify_voice',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Угроза приходит не только как грубая сила; очень часто она приходит '
            'как умная, обаятельная и деvious manipulation.'
        ),
        'tags': ['fear', 'deception', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should include deception/manipulation as a live danger.',
        'source_names': {'would-you-love-the-same-man'},
        'patterns': [
            r'susceptible to very devious manipulation',
            r'alert to that form of deception as a threat',
            r'psychopathic men',
        ],
    },
    {
        'move_name': 'regret-follows-cost-asymmetry',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'После импульсивной близости сожаление обычно растёт там, где цена '
            'решения была выше, чем человек признал в момент выбора.'
        ),
        'tags': ['relationship', 'regret', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should ask not what happened, but what it cost.',
        'source_names': {'would-you-love-the-same-man'},
        'patterns': [
            r'women experiencing more sexual regret when the costs are higher',
            r'sold herself short',
            r'risk of that is too high',
        ],
    },
    {
        'move_name': 'hormones-are-part-of-the-self',
        'pattern_type': 'clarify_voice',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Нельзя честно разбираться с собой, если делать вид, будто тело и его '
            'биология — это внешний шум, а не часть самой личности.'
        ),
        'tags': ['self', 'embodiment', 'clarify'],
        'score': 6,
        'note': 'Useful when clarify should bring embodiment back into self-understanding.',
        'source_names': {'would-you-love-the-same-man'},
        'patterns': [
            r'you are your hormones',
            r'our hormones are part of the signaling machinery',
            r'part of the machinery',
        ],
    },
    {
        'move_name': 'don-t-solve-a-problem-you-don-t-have',
        'pattern_type': 'clarify_voice',
        'theme_name': 'parenting/boundaries',
        'profile_hint': 'parenting-boundaries',
        'pattern_text': (
            'Не нужно решать заранее то, что ещё не стало живой проблемой; '
            'сначала смотри на реальный сигнал и бери cue из ситуации.'
        ),
        'tags': ['parenting', 'timing', 'clarify'],
        'score': 7,
        'note': 'Useful for parenting/scope clarifies.',
        'source_names': {'master-relationships'},
        'patterns': [
            r'take your cues from your children',
            r'you don[\' ]?t need to solve a problem you don[\' ]?t have',
            r'if they[\' ]?re thriving, then i would leave that question alone',
        ],
    },
    {
        'move_name': 'selection-sees-investment',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'В вопросах притяжения и парной связи важны не ярлыки и не теория, '
            'а реальный паттерн вложения, риска и выбора.'
        ),
        'tags': ['relationship', 'attraction', 'clarify'],
        'score': 6,
        'note': 'Use for higher-level sexuality/intimacy framing.',
        'source_names': {'would-you-love-the-same-man'},
        'patterns': [
            r'it[\' ]?s only what selection sees that matters',
            r'what it sees is investment',
        ],
    },
    {
        'move_name': 'harsh-truth-can-soften-suffering',
        'pattern_type': 'clarify_voice',
        'theme_name': 'tragedy/suffering',
        'profile_hint': 'tragedy-and-bitterness',
        'pattern_text': (
            'Иногда правда жёстка, но ясное понимание жёсткости жизни всё равно '
            'лучше слепоты, потому что слепота делает страдание ещё бессмысленнее.'
        ),
        'tags': ['tragedy', 'truth', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should admit harsh reality without collapsing into bitterness.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'understanding that makes it less harsh',
            r'harshness of life',
        ],
    },
    {
        'move_name': 'aim-is-targeted-action-and-speech',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Направление проявляется не как абстрактное настроение, а как '
            'умение целиться, бить в цель и говорить достаточно точно, чтобы '
            'действие вообще стало возможным.'
        ),
        'tags': ['meaning', 'aim', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should connect aimlessness with vague speech and unfocused action.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'hitting the target and aiming',
            r'being specific with words',
            r'goal-oriented action',
        ],
    },
    {
        'move_name': 'status-grows-through-reciprocity',
        'pattern_type': 'clarify_voice',
        'theme_name': 'resentment/conflict',
        'profile_hint': 'resentment-buildup',
        'pattern_text': (
            'Долгая социальная сила часто строится не на захвате, а на '
            'щедрости, которая вызывает reciprocity и создаёт кредит доверия.'
        ),
        'tags': ['resentment', 'reciprocity', 'clarify'],
        'score': 7,
        'note': 'Useful when clarify should shift from grievance to reciprocity and earned standing.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'store meat in your status among the hunting group',
            r'if you[\' ]?re generous and you share',
            r'reciprocity dependent',
        ],
    },
    {
        'move_name': 'competence-beats-domination',
        'pattern_type': 'clarify_voice',
        'theme_name': 'resentment/conflict',
        'profile_hint': 'resentment-buildup',
        'pattern_text': (
            'Не всякая иерархия держится на голом подавлении; очень часто '
            'устойчивое превосходство строится на способности реально приносить '
            'пользу.'
        ),
        'tags': ['resentment', 'competence', 'clarify'],
        'score': 8,
        'note': 'Use when resentment should be reframed away from lazy oppression narratives.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'we don[\' ]?t mean oppression',
            r'competence model',
            r'benefit conferral',
        ],
    },
    {
        'move_name': 'integrated-strength-beats-narcissism',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Сила становится пригодной для близости не тогда, когда она '
            'нарциссически выпячена, а когда она приручена и поставлена на службу '
            'чему-то большему.'
        ),
        'tags': ['relationship', 'strength', 'clarify'],
        'score': 7,
        'note': 'Useful when clarify should separate brute display from trustworthy strength.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'beast who[\' ]?s a beast but he[\' ]?s tameable',
            r'capacity to inflict cost',
            r'gaston',
        ],
    },
    {
        'move_name': 'inexperience-confuses-control-with-competence',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'Неопытность делает человека уязвимым к подмене: control и dark-triad '
            'display легко принимаются за competence и value.'
        ),
        'tags': ['relationship', 'naivete', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should account for naive attraction to false strength.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'not that easy to distinguish',
            r'dark triad types can feign',
            r'ensnare naive women',
        ],
    },
    {
        'move_name': 'attention-reveals-what-you-value',
        'pattern_type': 'clarify_voice',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'То, на что уходит внимание, почти всегда выдаёт реальную иерархию '
            'ценностей лучше, чем декларации о принципах.'
        ),
        'tags': ['attention', 'value', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should ask what the user is already worshipping in practice.',
        'source_names': {'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'attention structure is an unbelievably reliable indicator',
            r'we don[\' ]?t devote our visual attentive resources',
            r'compete for attention',
        ],
    },
    {
        'move_name': 'unstable-young-men-no-access',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'Когда из области отношений исчезает реальный доступ к связи и '
            'взаимности, система быстро становится нестабильной.'
        ),
        'tags': ['relationship', 'instability', 'clarify'],
        'score': 5,
        'note': 'Broader cultural frame for intimacy/selection issues.',
        'source_names': {'w-lex'},
        'patterns': [
            r'most unstable social situation',
            r'young men with no access to women',
        ],
    },
    {
        'move_name': 'adventure-generates-attraction',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'scope-sexual-problems',
        'pattern_text': (
            'Притяжение чаще рождается не из жалобы на рынок, а из движения в '
            'сторону adventure, риска и становления.'
        ),
        'tags': ['relationship', 'adventure', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should redirect isolation toward growth and adventure.',
        'source_names': {'w-lex'},
        'patterns': [
            r'pathway of Adventure itself is the best Pathway to romantic attractiveness',
            r'beauty and the beast',
            r'default value of a 15-year-old male on the mating market',
        ],
    },
    {
        'move_name': 'envy-points-to-buried-desire',
        'pattern_type': 'clarify_voice',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Зависть полезна хотя бы тем, что выдаёт скрытое желание: она '
            'показывает, чего человек на самом деле хочет, даже если не решается '
            'сказать это прямо.'
        ),
        'tags': ['envy', 'desire', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should turn envy into a diagnostic of value.',
        'source_names': {'w-lex'},
        'patterns': [
            r'the only reason you[\' ]?re envious',
            r'what am i envious of',
            r'benchmark for tomorrow is you today',
        ],
    },
    {
        'move_name': 'orient-upward-to-see-truth',
        'pattern_type': 'clarify_voice',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Без серьёзной upward orientation человек быстро теряет способность '
            'различать правду и ложь даже в собственной жизни.'
        ),
        'tags': ['truth', 'orientation', 'clarify'],
        'score': 9,
        'note': 'Use when clarify should ask what the user is actually orienting life toward.',
        'source_names': {'w-lex'},
        'patterns': [
            r'orient your life upward',
            r'can[\' ]?t distinguish between truth and falsehood',
            r'aim upward and to tell the truth',
        ],
    },
    {
        'move_name': 'aim-opens-a-pathway',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Как только появляется реальная цель, мир перестаёт быть туманом и '
            'начинает делиться на препятствия и на то, что двигает вперёд.'
        ),
        'tags': ['meaning', 'path', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should connect aim with perceptual structure.',
        'source_names': {'w-lex'},
        'patterns': [
            r'set your path with your orientation',
            r'as soon as you have a goal a pathway opens up',
            r'things that move you forward',
        ],
    },
    {
        'move_name': 'one-encouraging-figure-can-anchor-a-life',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Иногда человеку достаточно одной действительно encouraging фигуры, '
            'чтобы снова увидеть путь, на который стоит становиться.'
        ),
        'tags': ['meaning', 'model', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should ask who still calls the user upward.',
        'source_names': {'w-lex'},
        'patterns': [
            r'at least one figure in their life that[\' ]?s encouraging',
            r'pathway forward',
            r'found the pattern that guided them',
        ],
    },
    {
        'move_name': 'love-includes-standards-and-encouragement',
        'pattern_type': 'clarify_voice',
        'theme_name': 'relationship/intimacy',
        'profile_hint': 'relationship-knot',
        'pattern_text': (
            'Любовь — это не только acceptance; это ещё encouragement, standards '
            'и готовность сказать: нет, так ниже тебя, ты способен на большее.'
        ),
        'tags': ['relationship', 'love', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should frame love as demand plus encouragement, not indulgence.',
        'source_names': {'w-lex'},
        'patterns': [
            r'apply the highest possible standards',
            r'love isn[\' ]?t just acceptance',
            r'you[\' ]?re capable of more',
        ],
    },
    {
        'move_name': 'love-needs-standards-not-indulgence',
        'pattern_type': 'framing_move',
        'theme_name': 'parenting/boundaries',
        'profile_hint': 'parenting-boundaries',
        'pattern_text': (
            'Любовь к ребёнку не сводится к смягчению мира; она включает стандарт, '
            'который помогает ему стать сильнее, а не просто чувствовать себя спокойнее сейчас.'
        ),
        'tags': ['parenting', 'framing', 'boundaries'],
        'score': 8,
        'note': 'Frame parenting as standards plus encouragement, not indulgence.',
        'source_names': {'w-lex'},
        'patterns': [
            r'love isn[\' ]?t just acceptance',
            r'you[\' ]?re capable of more',
            r'apply the highest possible standards',
        ],
    },
    {
        'move_name': 'narrow-parenting-to-child-or-parent-fear',
        'pattern_type': 'narrowing_question',
        'theme_name': 'parenting/boundaries',
        'profile_hint': 'parenting-boundaries',
        'pattern_text': (
            'Скажи прямо: тебя здесь больше пугает поведение ребёнка, собственная вина '
            'или необходимость позволить ему столкнуться с реальностью?'
        ),
        'tags': ['parenting', 'question', 'boundaries'],
        'score': 7,
        'note': 'Narrow parenting asks to the core fear or burden.',
        'source_names': {'w-lex', 'master-relationships'},
        'patterns': [
            r'love isn[\' ]?t just acceptance',
            r'support the mother',
            r'you[\' ]?re capable of more',
        ],
    },
    {
        'move_name': 'fear-needs-its-proper-place',
        'pattern_type': 'clarify_voice',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Страх, боль и гнев не исчезают из хорошей жизни; вопрос в том, '
            'занимают ли они своё proper place или уже управляют человеком '
            'целиком.'
        ),
        'tags': ['fear', 'order', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should sort useful fear from ruling fear.',
        'source_names': {'w-lex'},
        'patterns': [
            r'everything in its proper place',
            r'without fear',
            r'beneficial even though they can cause great suffering',
        ],
    },
    {
        'move_name': 'fear-points-to-the-price-of-value',
        'pattern_type': 'framing_move',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Там, где страх силён, почти всегда стоит нечто достаточно ценное, '
            'чтобы за него пришлось платить.'
        ),
        'tags': ['fear', 'value', 'framing'],
        'score': 8,
        'note': 'Frame fear as the shadow of value and price.',
        'source_names': {'w-lex', 'evolution-sex-and-desire-david-buss-ep-235'},
        'patterns': [
            r'you have to be able to say no',
            r'understanding that makes it less harsh',
            r'capacity to inflict cost',
        ],
    },
    {
        'move_name': 'narrow-fear-to-what-might-be-lost',
        'pattern_type': 'narrowing_question',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Скажи точнее: ты боишься потерять одобрение, безопасность, власть или привычную идентичность?'
        ),
        'tags': ['fear', 'question', 'value'],
        'score': 7,
        'note': 'Narrow fear to the main threatened value.',
        'source_names': {'w-lex', 'would-you-love-the-same-man'},
        'patterns': [
            r'you have to be able to say no',
            r'costs are higher',
            r'alert to that form of deception as a threat',
        ],
    },
    {
        'move_name': 'goodness-requires-the-capacity-to-say-no',
        'pattern_type': 'clarify_voice',
        'theme_name': 'parenting/boundaries',
        'profile_hint': 'parenting-boundaries',
        'pattern_text': (
            'Хорошие границы требуют не просто доброты, а реальной способности '
            'сказать no и выдержать последствия этого нет.'
        ),
        'tags': ['boundaries', 'strength', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should frame boundaries as strength, not cruelty.',
        'source_names': {'w-lex'},
        'patterns': [
            r'a good man has to be formidable',
            r'you have to be able to say no',
            r'100% certainty',
        ],
    },
    {
        'move_name': 'weakness-is-not-virtue',
        'pattern_type': 'clarify_voice',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Слабость сама по себе не добродетель; если человек не умеет быть '
            'опасным, его мягкость ещё не означает нравственную зрелость.'
        ),
        'tags': ['strength', 'virtue', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should separate harmlessness from goodness.',
        'source_names': {'w-lex'},
        'patterns': [
            r'weak men aren[\' ]?t good',
            r'they[\' ]?re just weak',
        ],
    },
    {
        'move_name': 'careful-conduct-prevents-only-bad-options',
        'pattern_type': 'clarify_voice',
        'theme_name': 'fear/value',
        'profile_hint': 'fear-and-price',
        'pattern_text': (
            'Осторожная и честная жизнь нужна ещё и затем, чтобы не довести себя '
            'до положения, где впереди остаются только плохие варианты.'
        ),
        'tags': ['fear', 'consequence', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should highlight accumulated consequence rather than one-off failure.',
        'source_names': {'w-lex'},
        'patterns': [
            r'variety of bad options',
            r'conduct yourself very carefully',
        ],
    },
    {
        'move_name': 'good-faith-alliance-with-truth',
        'pattern_type': 'clarify_voice',
        'theme_name': 'truth/self-deception',
        'profile_hint': 'self-deception',
        'pattern_text': (
            'Правда становится рабочей опорой только тогда, когда человек решает '
            'двигаться в good faith и не делает удобный outcome своим божеством.'
        ),
        'tags': ['truth', 'faith', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should ask what the user serves: truth or outcome.',
        'source_names': {'w-lex'},
        'patterns': [
            r'move forward in good faith',
            r'truth is the deity',
            r'making the outcome your deity',
        ],
    },
    {
        'move_name': 'destiny-announces-itself-through-interest',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Направление редко выдумывается с нуля; чаще оно announces itself в '
            'том, что человека действительно захватывает, тревожит и зовёт '
            'вперёд.'
        ),
        'tags': ['meaning', 'calling', 'clarify'],
        'score': 8,
        'note': 'Use when clarify should ask what the person is already being called toward.',
        'source_names': {'w-lex'},
        'patterns': [
            r'destiny announces itself',
            r'certain things in your field of perception are illuminated',
            r'things draw you into the world',
        ],
    },
    {
        'move_name': 'voluntary-agreement-beats-compulsion',
        'pattern_type': 'clarify_voice',
        'theme_name': 'resentment/conflict',
        'profile_hint': 'resentment-buildup',
        'pattern_text': (
            'Порядок, построенный на добровольном соглашении, качественно лучше '
            'порядка, построенного на compulsion; иначе resentment накапливается '
            'внутри самой структуры.'
        ),
        'tags': ['resentment', 'voluntary', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should separate commitment from coercion.',
        'source_names': {'w-lex'},
        'patterns': [
            r'voluntary play',
            r'power and compulsion',
            r'voluntary joint agreement',
        ],
    },
    {
        'move_name': 'disunity-breeds-anxiety-and-hopelessness',
        'pattern_type': 'clarify_voice',
        'theme_name': 'meaning/direction',
        'profile_hint': 'lost-and-aimless',
        'pattern_text': (
            'Когда в человеке или в его ценностях нет объединяющего центра, цена '
            'этого обычно платится goal confusion, anxiety и hopelessness.'
        ),
        'tags': ['meaning', 'unity', 'clarify'],
        'score': 7,
        'note': 'Use when clarify should frame confusion as disunity rather than lack of data.',
        'source_names': {'w-lex'},
        'patterns': [
            r'cost of that disunity',
            r'goal confusion anxiety and hopelessness',
            r'value systems tend towards a unity',
        ],
    },
]


def _snippet_around_match(text: str, match: re.Match, window: int = 520) -> str:
    start = max(0, match.start() - window // 2)
    end = min(len(text), match.end() + window // 2)
    snippet = text[start:end]
    snippet = re.sub(r'\s+', ' ', snippet).strip()
    if len(snippet) > window:
        snippet = snippet[:window].rsplit(' ', 1)[0].rstrip()
    return snippet


def _iter_transcript_chunks(cur):
    rows = cur.execute(
        '''
        SELECT d.id AS document_id,
               d.source_pdf,
               dc.id AS chunk_id,
               dc.content
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.revision_id = d.active_revision_id
        ORDER BY d.id ASC, dc.chunk_index ASC
        '''
    ).fetchall()
    for document_id, source_pdf, chunk_id, content in rows:
        source_name = friendly_source_name(source_pdf)
        if source_name not in TARGET_SOURCE_NAMES:
            continue
        if not content:
            continue
        yield {
            'document_id': document_id,
            'source_name': source_name,
            'chunk_id': chunk_id,
            'content': content,
        }


def load_voice_patterns() -> dict:
    inserted = 0
    matched_moves: set[str] = set()
    matched_sources: set[str] = set()
    matched_pattern_types: set[str] = set()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM voice_patterns')
        for row in _iter_transcript_chunks(cur):
            content = row['content']
            lowered = content.lower()
            for rule in VOICE_PATTERN_RULES:
                if row['source_name'] not in rule['source_names']:
                    continue
                first_match = None
                for pattern in rule['patterns']:
                    first_match = re.search(pattern, lowered, flags=re.IGNORECASE)
                    if first_match:
                        break
                if not first_match:
                    continue
                excerpt = _snippet_around_match(content, first_match)
                cur.execute(
                    '''
                    INSERT OR IGNORE INTO voice_patterns (
                        source_name, document_id, chunk_id, pattern_type,
                        theme_name, profile_hint, move_name, pattern_text,
                        evidence_excerpt, tags_json, score, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        row['source_name'],
                        row['document_id'],
                        row['chunk_id'],
                        rule['pattern_type'],
                        rule['theme_name'],
                        rule['profile_hint'],
                        rule['move_name'],
                        rule['pattern_text'],
                        excerpt,
                        json.dumps(rule['tags'], ensure_ascii=False),
                        int(rule['score']),
                        rule['note'],
                    ),
                )
                if cur.rowcount:
                    inserted += 1
                    matched_moves.add(rule['move_name'])
                    matched_sources.add(row['source_name'])
                    matched_pattern_types.add(rule['pattern_type'])

        count = cur.execute('SELECT COUNT(*) FROM voice_patterns').fetchone()[0]
    return {
        'voice_patterns': count,
        'inserted': inserted,
        'matched_moves': sorted(matched_moves),
        'matched_sources': sorted(matched_sources),
        'matched_pattern_types': sorted(matched_pattern_types),
    }


def load_profile_voice_bundle(profile_hint: str, fallback_profiles: tuple[str, ...] = ()) -> dict:
    """Load DB-backed voice patterns for one clarify profile.

    Returns a dict with:
    - ``moves``: best row per move name
    - ``typed_moves``: best row per pattern type and move name
    - ``rows``: all matched rows ordered by score
    - ``source_refs``: compact source labels
    """
    profiles = tuple(dict.fromkeys(
        profile for profile in (profile_hint, *fallback_profiles) if profile
    ))
    if not profiles:
        return {'moves': {}, 'rows': [], 'source_refs': []}

    placeholders = ', '.join('?' for _ in profiles)
    with connect() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            f'''
            SELECT source_name, profile_hint, pattern_type, move_name,
                   pattern_text, evidence_excerpt, score, tags_json
            FROM voice_patterns
            WHERE profile_hint IN ({placeholders})
            ORDER BY score DESC, pattern_type ASC, source_name ASC, move_name ASC, id ASC
            ''',
            profiles,
        ).fetchall()

    packed_rows = []
    moves: dict[str, dict] = {}
    typed_moves: dict[str, dict[str, dict]] = {}
    source_refs: list[str] = []
    seen_sources: set[str] = set()
    for source_name, profile, pattern_type, move_name, pattern_text, evidence_excerpt, score, tags_json in rows:
        item = {
            'source_name': source_name,
            'profile_hint': profile or '',
            'pattern_type': pattern_type,
            'move_name': move_name,
            'pattern_text': pattern_text,
            'evidence_excerpt': evidence_excerpt,
            'score': int(score or 0),
            'tags': json.loads(tags_json or '[]'),
        }
        packed_rows.append(item)
        moves.setdefault(move_name, item)
        typed_moves.setdefault(pattern_type or '', {}).setdefault(move_name, item)
        if source_name and source_name not in seen_sources:
            seen_sources.add(source_name)
            source_refs.append(source_name)

    return {
        'moves': moves,
        'typed_moves': typed_moves,
        'rows': packed_rows,
        'source_refs': source_refs,
    }


def summarize_voice_patterns(limit: int = 5) -> dict:
    """Return a compact DB-backed summary of extracted transcript voice utility."""
    limit = max(1, int(limit))
    with connect() as conn:
        cur = conn.cursor()
        total = cur.execute('SELECT COUNT(*) FROM voice_patterns').fetchone()[0]
        by_type = dict(cur.execute(
            'SELECT pattern_type, COUNT(*) FROM voice_patterns '
            'GROUP BY pattern_type ORDER BY COUNT(*) DESC, pattern_type ASC'
        ).fetchall())
        by_source = dict(cur.execute(
            'SELECT source_name, COUNT(*) FROM voice_patterns '
            'GROUP BY source_name ORDER BY COUNT(*) DESC, source_name ASC'
        ).fetchall())
        by_profile = dict(cur.execute(
            'SELECT COALESCE(profile_hint, ""), COUNT(*) FROM voice_patterns '
            'GROUP BY profile_hint ORDER BY COUNT(*) DESC, profile_hint ASC'
        ).fetchall())
        by_move = dict(cur.execute(
            'SELECT move_name, COUNT(*) FROM voice_patterns '
            'GROUP BY move_name ORDER BY COUNT(*) DESC, move_name ASC'
        ).fetchall())
        top_rows = cur.execute(
            '''
            SELECT source_name, profile_hint, move_name, score, evidence_excerpt
            FROM voice_patterns
            ORDER BY score DESC, source_name ASC, move_name ASC
            LIMIT ?
            ''',
            (limit,),
        ).fetchall()

    themes = Counter()
    for rule in VOICE_PATTERN_RULES:
        themes[rule['theme_name']] += 1

    examples = [
        {
            'source_name': row[0],
            'profile_hint': row[1] or '',
            'move_name': row[2],
            'score': row[3],
            'evidence_excerpt': row[4],
        }
        for row in top_rows
    ]

    return {
        'voice_patterns': total,
        'target_sources': sorted(TARGET_SOURCE_NAMES),
        'rule_count': len(VOICE_PATTERN_RULES),
        'by_type': by_type,
        'themes_in_rules': dict(sorted(themes.items())),
        'by_source': by_source,
        'by_profile': by_profile,
        'by_move': by_move,
        'examples': examples,
    }
