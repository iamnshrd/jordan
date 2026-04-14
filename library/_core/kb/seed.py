#!/usr/bin/env python3
"""Seed data for the V3 knowledge base: routes, bridges, steps, motifs, quality, packs."""
from library.db import connect, get_id

# ── seed_v3 data ─────────────────────────────────────────────────────────────

SOURCE_ROUTE_ROWS = [
    ('12-rules', 'shame-self-contempt', 9, 'best first-order shame repair'),
    ('12-rules', 'basic-discipline', 10, 'best first stabilization source'),
    ('beyond-order', 'career-vocation', 10, 'best mature vocation source'),
    ('beyond-order', 'relationship-maintenance', 10, 'best romance maintenance source'),
    ('maps-of-meaning', 'mythic-meaning-collapse', 10, 'best deep collapse source'),
    ('maps-of-meaning', 'chaos-unknown', 9, 'best symbolic chaos source'),
]

BRIDGES = [
    ('career-bridge', 'meaning', 'aimlessness', 'Проблема не только в тумане, а в отсутствии выбранного бремени.', 'Ты избегаешь ответственности за выбор направления.', 'Выбери одно серьёзное обязательство на ближайший цикл.', 'Дальше нужно строить идентичность вокруг добровольно принятой ответственности.', 'hard', 'manual v3 seed'),
    ('shame-bridge', 'suffering', 'avoidance-loop', 'Здесь есть не просто боль, а саморазрушительное отождествление себя с провалом.', 'Ты избегаешь точного признания поступка, заменяя его тотальным осуждением себя.', 'Назови один конкретный проступок и один конкретный ремонтный шаг.', 'Долгосрочно нужно отделить вину от самоаннигиляции.', 'reflective', 'manual v3 seed'),
    ('relationship-bridge', 'responsibility', 'resentment-loop', 'Здесь копится не только конфликт, но и невысказанная обида.', 'Ты избегаешь прямого разговора и ясной границы.', 'Сформулируй один упрёк и одну границу без театрализованной вражды.', 'Дальше отношения держатся только на правде, переговорах и дисциплине.', 'default', 'manual v3 seed'),
    ('addiction-bridge', 'order-and-chaos', 'avoidance-loop', 'Здесь хаос не снаружи — он внутри, и зависимость стала единственным регулятором.', 'Ты перестал выстраивать внутренний порядок и отдал контроль суррогатному успокоению.', 'Восстанови одну рутину, которая не зависит от вещества или привычки.', 'Долгосрочно нужно заново строить структуру дня вокруг добровольной дисциплины, а не вокруг утоления.', 'hard', 'manual v3 bridge expansion'),
    ('parenting-bridge', 'responsibility', 'avoidance-loop', 'Здесь есть не просто конфликт с ребёнком, а уклонение от границ из страха стать тираном.', 'Ты подменяешь ответственность за структуру тревогой за отношения.', 'Назови одну границу, которую ты не обозначаешь, и обозначь её сегодня без объяснений на три абзаца.', 'Долгосрочно ребёнку нужна не мягкость, а предсказуемый порядок с ясными правилами.', 'default', 'manual v3 bridge expansion'),
    ('avoidance-bridge', 'order-and-chaos', 'avoidance-loop', 'Проблема не в мотивации, а в том, что структура распалась и каждый шаг кажется одинаково бессмысленным.', 'Ты ждёшь вдохновения вместо дисциплины и путаешь бездействие с обдумыванием.', 'Составь список из трёх дел, которые ты откладываешь, и сделай первое, не дожидаясь настроения.', 'Долгосрочно нужно приучить себя к тому, что действие предшествует мотивации, а не наоборот.', 'hard', 'manual v3 bridge expansion'),
    ('self-deception-bridge', 'truth', 'avoidance-loop', 'Проблема не в незнании, а в том, что ты уже знаешь правду, но отказываешься её назвать.', 'Ты защищаешь версию реальности, которая удобна, но разрушительна.', 'Запиши одну вещь, которую ты точно знаешь, но не называешь вслух.', 'Долгосрочно нужно перестроить отношение к правде: не как к оружию, а как к фундаменту.', 'reflective', 'manual v3 bridge expansion'),
]

NEXT_STEPS = [
    ('one-duty', 'meaning', 'aimlessness', 'career-vocation', 'Назови одну обязанность, которую ты перестал нести, и верни её себе добровольно.', 'medium', 'today', '', 'manual v3 seed'),
    ('one-repair-act', 'suffering', 'avoidance-loop', 'shame-self-contempt', 'Сделай один конкретный восстановительный шаг вместо общего самоунижения.', 'low', 'today', '', 'manual v3 seed'),
    ('one-hard-conversation', 'responsibility', 'resentment-loop', 'relationship-maintenance', 'Проведи один трудный прямой разговор без молчаливой обиды и без истерики.', 'high', 'this-week', '', 'manual v3 seed'),
]

QUOTE_PACKS = [
    ('career-pack', 'career-vocation', 'beyond-order,12-rules', 'discipline-quote,principle-quote', 'manual v3 seed'),
    ('shame-pack', 'shame-self-contempt', '12-rules,maps-of-meaning', 'shame-quote,principle-quote', 'manual v3 seed'),
    ('relationship-pack', 'relationship-maintenance', 'beyond-order,12-rules', 'relationship-quote,resentment-quote', 'manual v3 seed'),
]

ARCHETYPE_INTERVENTIONS = [
    ('career-vocation', 'narrow-burden', 'manual v3 seed'),
    ('shame-self-contempt', 'separate-guilt-from-identity', 'manual v3 seed'),
    ('relationship-maintenance', 'truthful-negotiation', 'manual v3 seed'),
    ('addiction-chaos', 'narrow-burden', 'manual v3 bridge expansion'),
    ('parenting-overprotection', 'truthful-negotiation', 'manual v3 bridge expansion'),
    ('avoidance-paralysis', 'narrow-burden', 'manual v3 bridge expansion'),
    ('self-deception', 'separate-guilt-from-identity', 'manual v3 bridge expansion'),
]

THEME_STEP_LINKS = [
    ('meaning', 'one-duty'),
    ('suffering', 'one-repair-act'),
    ('responsibility', 'one-hard-conversation'),
]

PATTERN_STEP_LINKS = [
    ('aimlessness', 'one-duty'),
    ('avoidance-loop', 'one-repair-act'),
    ('resentment-loop', 'one-hard-conversation'),
]

ARCHETYPE_PACKS = [
    ('career-vocation', 'career-pack'),
    ('shame-self-contempt', 'shame-pack'),
    ('relationship-maintenance', 'relationship-pack'),
]

# ── seed_v3_links data ───────────────────────────────────────────────────────

CASE_LINKS = [
    ('No decision is itself a decision', 'career-vocation', 'narrow-burden'),
    ('Resentment-deceit-arrogance triad', 'relationship-maintenance', 'truthful-negotiation'),
    ('Shame marks exposed insufficiency before reorganization', 'shame-self-contempt', 'separate-guilt-from-identity'),
    ('Parenting requires boundaries before resentment builds', 'relationship-maintenance', 'truthful-negotiation'),
    ('Meaning is a lived map, not an abstract slogan', 'career-vocation', 'narrow-burden'),
]

CONFIDENCE_ROWS = [
    ('case', 'No decision is itself a decision', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('case', 'Resentment-deceit-arrogance triad', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('case', 'Shame marks exposed insufficiency before reorganization', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'career-bridge', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'shame-bridge', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'relationship-bridge', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'addiction-bridge', 'medium', 'manual-curated', 1, 1, 'manual v3 bridge expansion'),
    ('bridge', 'parenting-bridge', 'medium', 'manual-curated', 1, 1, 'manual v3 bridge expansion'),
    ('bridge', 'avoidance-bridge', 'medium', 'manual-curated', 1, 1, 'manual v3 bridge expansion'),
    ('bridge', 'self-deception-bridge', 'medium', 'manual-curated', 1, 1, 'manual v3 bridge expansion'),
]

# ── seed_v3_motifs data ──────────────────────────────────────────────────────

ANTI_PATTERN_ROWS_MOTIFS = [
    ('career-vocation', 'abstract-inflation', 'manual v3 seed'),
    ('shame-self-contempt', 'identity-annihilation', 'manual v3 seed'),
    ('relationship-maintenance', 'silent-resentment-spiral', 'manual v3 seed'),
    ('addiction-chaos', 'willpower-fantasy', 'manual v3 bridge expansion'),
    ('parenting-overprotection', 'guilt-driven-capitulation', 'manual v3 bridge expansion'),
    ('avoidance-paralysis', 'analysis-paralysis', 'manual v3 bridge expansion'),
    ('self-deception', 'comfortable-fog', 'manual v3 bridge expansion'),
]

MOTIF_LINKS = [
    ('dragon', 'The heroic stance is voluntary confrontation with the unknown', 'narrow-burden'),
    ('dragon', 'The dragon of chaos guards the next stage of growth', 'narrow-burden'),
    ('dragon', 'The unknown is both threat and possibility', 'narrow-burden'),
    ('burden', 'Responsibility and meaning are linked', 'narrow-burden'),
    ('burden', 'Opportunity appears in abandoned responsibility', 'narrow-burden'),
    ('burden', 'No decision is itself a decision', 'narrow-burden'),
    ('burden', 'Parenting requires boundaries before resentment builds', 'truthful-negotiation'),
    ('burden', 'Relationship maintenance is active work', 'truthful-negotiation'),
]

# ── seed_v3_quality data ─────────────────────────────────────────────────────

ANTI_PATTERN_ROWS_QUALITY = [
    ('career-vocation', 'self-dramatizing-aimlessness', 'manual v3 quality seed'),
    ('career-vocation', 'abstract-inflation', 'manual v3 quality seed'),
    ('shame-self-contempt', 'identity-annihilation', 'manual v3 quality seed'),
    ('shame-self-contempt', 'moral-grandiosity-through-self-hatred', 'manual v3 quality seed'),
    ('relationship-maintenance', 'silent-resentment-spiral', 'manual v3 quality seed'),
    ('relationship-maintenance', 'indirect-hostility', 'manual v3 quality seed'),
]

CONFIDENCE_CASE_NAMES = [
    'No decision is itself a decision',
    'Meaning is a lived map, not an abstract slogan',
    'The heroic stance is voluntary confrontation with the unknown',
    'Relationship maintenance is active work',
    'Parenting requires boundaries before resentment builds',
    'Truth repairs structure',
    'Self-contempt destroys correction capacity',
]

CONFIDENCE_PACKS = ['career-pack', 'shame-pack', 'relationship-pack']
CONFIDENCE_STEPS = ['one-duty', 'one-repair-act', 'one-hard-conversation']

# ── seed_v3_runtime_links data ───────────────────────────────────────────────

SOURCE_ROUTE_UPSERT = [
    ('12-rules', 'career-vocation', 6, 'secondary support for vocation'),
    ('12-rules', 'relationship-maintenance', 7, 'truth/boundary backup source'),
    ('12-rules', 'mythic-meaning-collapse', 3, 'weak symbolic source'),
    ('beyond-order', 'shame-self-contempt', 5, 'secondary shame integration source'),
    ('beyond-order', 'mythic-meaning-collapse', 6, 'secondary symbolic source'),
    ('maps-of-meaning', 'career-vocation', 5, 'deep but secondary vocation source'),
    ('maps-of-meaning', 'shame-self-contempt', 7, 'deep shame/source of reorganization'),
]

ARCHETYPE_PACK_LINKS = [
    ('career-vocation', 'career-pack'),
    ('shame-self-contempt', 'shame-pack'),
    ('relationship-maintenance', 'relationship-pack'),
]

# ── seed_v3_steps data ───────────────────────────────────────────────────────

NEW_STEPS = [
    ('write-the-memory', 'suffering', 'avoidance-loop', 'shame-self-contempt', 'Опиши болезненное воспоминание полностью и без театрализации, пока оно не перестанет быть туманным хозяином поведения.', 'medium', 'this-week', '', 'manual v3 step seed'),
    ('state-the-resentment-directly', 'resentment', 'resentment-loop', 'relationship-maintenance', 'Назови один невысказанный упрёк прямо и без накопленной ядовитой риторики.', 'high', 'today', '', 'manual v3 step seed'),
    ('restore-local-order', 'order-and-chaos', 'avoidance-loop', 'basic-discipline', 'Наведи локальный порядок в одной зоне, чтобы вернуть себе ощущение агентности через действие.', 'low', 'today', '', 'manual v3 step seed'),
    ('name-the-lie', 'truth', 'avoidance-loop', 'shame-self-contempt', 'Сформулируй одну ложь или полуправду, на которой сейчас держится твоя проблема.', 'medium', 'today', '', 'manual v3 step seed'),
    ('replace-substance-with-routine', 'order-and-chaos', 'avoidance-loop', 'addiction-chaos', 'Выбери один момент дня, когда ты тянешься к привычке, и замени его одним физическим действием: прогулка, душ, уборка.', 'medium', 'today', '', 'manual v3 step expansion'),
    ('set-one-boundary-today', 'responsibility', 'avoidance-loop', 'parenting-overprotection', 'Обозначь ребёнку одну границу сегодня — кратко, без оправданий, и удержи её до конца дня.', 'medium', 'today', '', 'manual v3 step expansion'),
    ('do-the-first-thing', 'order-and-chaos', 'avoidance-loop', 'avoidance-paralysis', 'Открой список дел и сделай первое, даже если оно кажется ничтожным. Действие предшествует мотивации.', 'low', 'today', '', 'manual v3 step expansion'),
    ('write-the-truth-down', 'truth', 'avoidance-loop', 'self-deception', 'Запиши то, что ты знаешь, но не называешь вслух. Не для кого-то — для себя.', 'medium', 'today', '', 'manual v3 step expansion'),
    ('define-anti-ideal', 'meaning', 'aimlessness', 'career-vocation', 'Опиши подробно, кем ты точно не хочешь быть через 5 лет. Анти-идеал часто показывает направление яснее, чем позитивная мечта.', 'low', 'today', '', 'manual v3 step expansion'),
    ('specify-goal-and-failure', 'meaning', 'aimlessness', 'career-vocation', 'Сформулируй одну конкретную цель и одно реалистичное описание провала, если ты ничего не сделаешь.', 'medium', 'today', '', 'manual v3 step expansion'),
    ('audit-life-domains', 'meaning', 'aimlessness', '', 'Оцени по шкале 1-10 шесть областей жизни: карьера, здоровье, отношения, финансы, учёба, досуг. Выбери худшую и начни с неё.', 'low', 'today', '', 'manual v3 step expansion'),
    ('negotiate-work-reward', 'order-and-chaos', 'avoidance-loop', '', 'Договорись с собой: 90 минут работы — потом награда. Не наоборот.', 'low', 'today', '', 'manual v3 step expansion'),
    ('design-tomorrow-you-want', 'order-and-chaos', 'avoidance-loop', '', 'Каждый вечер письменно планируй завтрашний день так, чтобы ты хотел его прожить.', 'low', 'today', '', 'manual v3 step expansion'),
]

STEP_THEME_LINKS = [
    ('suffering', 'write-the-memory'),
    ('resentment', 'state-the-resentment-directly'),
    ('order-and-chaos', 'restore-local-order'),
    ('truth', 'name-the-lie'),
    ('order-and-chaos', 'replace-substance-with-routine'),
    ('responsibility', 'set-one-boundary-today'),
    ('order-and-chaos', 'do-the-first-thing'),
    ('truth', 'write-the-truth-down'),
    ('meaning', 'define-anti-ideal'),
    ('meaning', 'specify-goal-and-failure'),
    ('meaning', 'audit-life-domains'),
    ('order-and-chaos', 'negotiate-work-reward'),
    ('order-and-chaos', 'design-tomorrow-you-want'),
]

STEP_PATTERN_LINKS = [
    ('avoidance-loop', 'write-the-memory'),
    ('resentment-loop', 'state-the-resentment-directly'),
    ('avoidance-loop', 'restore-local-order'),
    ('avoidance-loop', 'name-the-lie'),
    ('avoidance-loop', 'replace-substance-with-routine'),
    ('avoidance-loop', 'set-one-boundary-today'),
    ('avoidance-loop', 'do-the-first-thing'),
    ('avoidance-loop', 'write-the-truth-down'),
    ('aimlessness', 'define-anti-ideal'),
    ('aimlessness', 'specify-goal-and-failure'),
    ('aimlessness', 'audit-life-domains'),
    ('avoidance-loop', 'negotiate-work-reward'),
    ('avoidance-loop', 'design-tomorrow-you-want'),
]

# ── seed_quote_pack_items data ───────────────────────────────────────────────

PACKS = {
    'career-pack': [
        'Imagine who you could be, and then aim single-mindedly at that.',
        'Do not do what you hate.',
        'The worst decision of all is no decision.',
        'Make yourself invaluable.',
    ],
    'shame-pack': [
        'Стыд за поступок можно исправлять. Но если ты превращаешь свою ошибку в доказательство собственной никчемности, ты разрушаешь возможность исправления.',
        'Shame can become the beginning of reformation if it is faced instead of denied.',
        'Shame and anxiety often signal the collapse of a former mode of adaptation.',
    ],
    'relationship-pack': [
        'Plan and work diligently to maintain the romance in your relationship.',
        'Do not allow yourself to become resentful, deceitful, or arrogant.',
        'If you have something difficult to say, silence may feel easier in the moment, but it is deadly in the long run.',
    ],
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_case_id(cur, name):
    row = cur.execute('SELECT id FROM cases WHERE case_name=?', (name,)).fetchone()
    return row[0] if row else None


def _get_bridge_id(cur, name):
    row = cur.execute('SELECT id FROM bridge_to_action_templates WHERE template_name=?', (name,)).fetchone()
    return row[0] if row else None


def _get_motif_id(cur, name):
    row = cur.execute('SELECT id FROM symbolic_motifs WHERE motif_name=?', (name,)).fetchone()
    return row[0] if row else None


def _get_pack_id(cur, name):
    row = cur.execute('SELECT id FROM route_quote_packs WHERE pack_name=?', (name,)).fetchone()
    return row[0] if row else None


def _get_step_id(cur, name):
    row = cur.execute('SELECT id FROM next_step_library WHERE step_name=?', (name,)).fetchone()
    return row[0] if row else None


def _get_quote_id(cur, text):
    row = cur.execute('SELECT id FROM quotes WHERE quote_text=?', (text,)).fetchone()
    return row[0] if row else None


# ── public seed functions ────────────────────────────────────────────────────

def seed_v3():
    """Seed V3 core data: routes, bridges, next steps, quote packs, interventions. Returns status."""
    with connect() as conn:
        cur = conn.cursor()

        cur.executemany(
            'INSERT OR REPLACE INTO source_route_strength (source_name, route_name, strength, note) VALUES (?, ?, ?, ?)',
            SOURCE_ROUTE_ROWS,
        )
        cur.executemany(
            'INSERT INTO bridge_to_action_templates (template_name, used_for_theme, used_for_pattern, diagnosis_stub, responsibility_stub, next_step_stub, long_term_stub, tone_profile, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'ON CONFLICT(template_name) DO UPDATE SET used_for_theme=excluded.used_for_theme, used_for_pattern=excluded.used_for_pattern, diagnosis_stub=excluded.diagnosis_stub, responsibility_stub=excluded.responsibility_stub, next_step_stub=excluded.next_step_stub, long_term_stub=excluded.long_term_stub, tone_profile=excluded.tone_profile, note=excluded.note',
            BRIDGES,
        )
        cur.executemany(
            'INSERT INTO next_step_library (step_name, used_for_theme, used_for_pattern, used_for_archetype, step_text, difficulty, time_horizon, contraindications, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'ON CONFLICT(step_name) DO UPDATE SET used_for_theme=excluded.used_for_theme, used_for_pattern=excluded.used_for_pattern, used_for_archetype=excluded.used_for_archetype, step_text=excluded.step_text, difficulty=excluded.difficulty, time_horizon=excluded.time_horizon, contraindications=excluded.contraindications, note=excluded.note',
            NEXT_STEPS,
        )
        cur.executemany(
            'INSERT INTO route_quote_packs (pack_name, route_name, preferred_sources, preferred_quote_types, note) VALUES (?, ?, ?, ?, ?) '
            'ON CONFLICT(pack_name) DO UPDATE SET route_name=excluded.route_name, preferred_sources=excluded.preferred_sources, preferred_quote_types=excluded.preferred_quote_types, note=excluded.note',
            QUOTE_PACKS,
        )
        cur.executemany(
            'INSERT OR REPLACE INTO archetype_interventions (archetype_name, intervention_pattern_name, note) VALUES (?, ?, ?)',
            ARCHETYPE_INTERVENTIONS,
        )

        for theme_name, step_name in THEME_STEP_LINKS:
            step_id = get_id(cur, 'next_step_library', 'step_name', step_name)
            if step_id is not None:
                cur.execute('INSERT OR REPLACE INTO theme_next_steps (theme_name, step_id, note) VALUES (?, ?, ?)', (theme_name, step_id, 'manual v3 seed'))

        for pattern_name, step_name in PATTERN_STEP_LINKS:
            step_id = get_id(cur, 'next_step_library', 'step_name', step_name)
            if step_id is not None:
                cur.execute('INSERT OR REPLACE INTO pattern_next_steps (pattern_name, step_id, note) VALUES (?, ?, ?)', (pattern_name, step_id, 'manual v3 seed'))

        for archetype_name, pack_name in ARCHETYPE_PACKS:
            pack_id = get_id(cur, 'route_quote_packs', 'pack_name', pack_name)
            if pack_id is not None:
                cur.execute('INSERT OR REPLACE INTO archetype_quote_packs (archetype_name, pack_id, note) VALUES (?, ?, ?)', (archetype_name, pack_id, 'manual v3 seed'))

    return 'seeded_v3'


def seed_v3_links():
    """Seed case-archetype links and confidence tags. Returns status."""
    with connect() as conn:
        cur = conn.cursor()

        for case_name, archetype_name, intervention_name in CASE_LINKS:
            case_id = _get_case_id(cur, case_name)
            if case_id:
                cur.execute('INSERT OR REPLACE INTO case_archetypes (case_id, archetype_name, note) VALUES (?, ?, ?)', (case_id, archetype_name, 'manual v3 seed'))
                cur.execute('INSERT OR REPLACE INTO case_interventions (case_id, intervention_pattern_name, note) VALUES (?, ?, ?)', (case_id, intervention_name, 'manual v3 seed'))

        for entity_type, entity_name, confidence, curation, source_count, manual_override, note in CONFIDENCE_ROWS:
            if entity_type == 'case':
                entity_id = _get_case_id(cur, entity_name)
            elif entity_type == 'bridge':
                entity_id = _get_bridge_id(cur, entity_name)
            else:
                entity_id = None
            if entity_id is not None:
                cur.execute(
                    'INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (entity_type, entity_id, confidence, curation, source_count, manual_override, note),
                )

    return 'seeded_v3_links'


def seed_v3_motifs():
    """Seed anti-patterns and motif-case/intervention links. Returns status."""
    with connect() as conn:
        cur = conn.cursor()

        for archetype_name, anti_pattern_name, note in ANTI_PATTERN_ROWS_MOTIFS:
            cur.execute('INSERT OR REPLACE INTO archetype_anti_patterns (archetype_name, anti_pattern_name, note) VALUES (?, ?, ?)', (archetype_name, anti_pattern_name, note))

        for motif_name, case_name, intervention_name in MOTIF_LINKS:
            motif_id = _get_motif_id(cur, motif_name)
            case_id = _get_case_id(cur, case_name)
            if motif_id and case_id:
                cur.execute('INSERT OR REPLACE INTO motif_cases (motif_id, case_id, note) VALUES (?, ?, ?)', (motif_id, case_id, 'manual v3 seed'))
                cur.execute('INSERT OR REPLACE INTO motif_interventions (motif_id, intervention_pattern_name, note) VALUES (?, ?, ?)', (motif_id, intervention_name, 'manual v3 seed'))

    return 'seeded_v3_motifs'


def seed_v3_quality():
    """Seed quality anti-patterns and extended confidence tags. Returns status."""
    with connect() as conn:
        cur = conn.cursor()

        for archetype_name, anti_pattern_name, note in ANTI_PATTERN_ROWS_QUALITY:
            cur.execute('INSERT OR REPLACE INTO archetype_anti_patterns (archetype_name, anti_pattern_name, note) VALUES (?, ?, ?)', (archetype_name, anti_pattern_name, note))

        for case_name in CONFIDENCE_CASE_NAMES:
            case_id = get_id(cur, 'cases', 'case_name', case_name)
            if case_id:
                cur.execute('INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)', ('case', case_id, 'high', 'manual-curated', 2, 1, 'manual v3 quality seed'))

        for pack_name in CONFIDENCE_PACKS:
            pack_id = get_id(cur, 'route_quote_packs', 'pack_name', pack_name)
            if pack_id:
                cur.execute('INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)', ('quote_pack', pack_id, 'high', 'manual-curated', 2, 1, 'manual v3 quality seed'))

        for step_name in CONFIDENCE_STEPS:
            step_id = get_id(cur, 'next_step_library', 'step_name', step_name)
            if step_id:
                cur.execute('INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)', ('next_step', step_id, 'high', 'manual-curated', 2, 1, 'manual v3 quality seed'))

    return 'seeded_v3_quality'


def seed_v3_runtime_links():
    """Seed secondary source-route strengths and archetype-pack links. Returns status."""
    with connect() as conn:
        cur = conn.cursor()

        cur.executemany(
            'INSERT OR REPLACE INTO source_route_strength (source_name, route_name, strength, note) VALUES (?, ?, ?, ?)',
            SOURCE_ROUTE_UPSERT,
        )

        for archetype_name, pack_name in ARCHETYPE_PACK_LINKS:
            pack_id = _get_pack_id(cur, pack_name)
            if pack_id:
                cur.execute('INSERT OR REPLACE INTO archetype_quote_packs (archetype_name, pack_id, note) VALUES (?, ?, ?)', (archetype_name, pack_id, 'manual runtime seed'))

    return 'seeded_v3_runtime_links'


def seed_v3_steps():
    """Seed additional next steps and their theme/pattern links. Returns status."""
    with connect() as conn:
        cur = conn.cursor()

        cur.executemany(
            'INSERT INTO next_step_library (step_name, used_for_theme, used_for_pattern, used_for_archetype, step_text, difficulty, time_horizon, contraindications, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'ON CONFLICT(step_name) DO UPDATE SET used_for_theme=excluded.used_for_theme, used_for_pattern=excluded.used_for_pattern, used_for_archetype=excluded.used_for_archetype, step_text=excluded.step_text, difficulty=excluded.difficulty, time_horizon=excluded.time_horizon, contraindications=excluded.contraindications, note=excluded.note',
            NEW_STEPS,
        )

        for theme_name, step_name in STEP_THEME_LINKS:
            step_id = _get_step_id(cur, step_name)
            if step_id:
                cur.execute('INSERT OR REPLACE INTO theme_next_steps (theme_name, step_id, note) VALUES (?, ?, ?)', (theme_name, step_id, 'manual v3 step seed'))

        for pattern_name, step_name in STEP_PATTERN_LINKS:
            step_id = _get_step_id(cur, step_name)
            if step_id:
                cur.execute('INSERT OR REPLACE INTO pattern_next_steps (pattern_name, step_id, note) VALUES (?, ?, ?)', (pattern_name, step_id, 'manual v3 step seed'))

    return 'seeded_v3_steps'


def seed_quote_pack_items():
    """Seed quote→pack membership. Returns status."""
    import logging
    _log = logging.getLogger('jordan')
    linked = 0
    not_found = 0
    with connect() as conn:
        cur = conn.cursor()
        for pack_name, quotes in PACKS.items():
            pack_id = _get_pack_id(cur, pack_name)
            if not pack_id:
                _log.warning('seed_quote_pack_items: pack %r not found, skipping', pack_name)
                continue
            for qt in quotes:
                qid = _get_quote_id(cur, qt)
                if qid:
                    cur.execute('INSERT OR REPLACE INTO quote_pack_items (pack_id, quote_id, note) VALUES (?, ?, ?)', (pack_id, qid, 'manual pack seed'))
                    linked += 1
                else:
                    not_found += 1
    if not_found:
        _log.warning('seed_quote_pack_items: %d quotes not found in DB', not_found)
    return f'seeded_quote_pack_items: linked={linked}, not_found={not_found}'
