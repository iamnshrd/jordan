#!/usr/bin/env python3
"""Canonical runtime KB query surface.

This module owns the structured retrieval bundle used by the runtime planner
and synthesis path. Older raw/inspection-style queries stay in ``query.py``.
"""
from library.db import connect


def confidence_rank(level, curation):
    score = 0
    if level == 'high':
        score += 3
    elif level == 'medium':
        score += 2
    elif level == 'low':
        score += 1
    if curation == 'manual-curated':
        score += 3
    return score


def bridge_bonus(template_name, theme, pattern):
    bonus = 0
    if template_name == 'anti-vagueness-bridge' and theme == 'meaning' and pattern == 'aimlessness':
        bonus += 5
    if template_name == 'self-negotiation-bridge' and pattern == 'avoidance-loop':
        bonus += 4
    return bonus


def next_step_bonus(step_name, theme, pattern, archetype):
    bonus = 0
    if archetype == 'career-vocation' and step_name in {'define-anti-ideal', 'specify-goal-and-failure'}:
        bonus += 5
    if pattern == 'avoidance-loop' and step_name in {'design-tomorrow-you-want', 'negotiate-work-reward'}:
        bonus += 4
    if theme == 'meaning' and step_name == 'audit-life-domains':
        bonus += 3
    return bonus


def query_v3(theme='', pattern='', archetype=''):
    """Main V3 query. Returns rich dict with bridge, next_step, quote_pack, etc."""
    with connect() as conn:
        cur = conn.cursor()

        bridge = None
        if theme or pattern:
            where_parts = []
            params = []
            if theme:
                where_parts.append('b.used_for_theme = ?')
                params.append(theme)
            if pattern:
                where_parts.append('b.used_for_pattern = ?')
                params.append(pattern)
            where_clause = ' AND '.join(where_parts) if where_parts else '1=1'
            candidates = cur.execute(f'''
                SELECT b.template_name, b.diagnosis_stub, b.responsibility_stub, b.next_step_stub, b.long_term_stub, b.tone_profile,
                       ct.confidence_level, ct.curation_level
                FROM bridge_to_action_templates b
                LEFT JOIN confidence_tags ct ON ct.entity_type='bridge' AND ct.entity_id=b.id
                WHERE {where_clause}
            ''', params).fetchall()
            if candidates:
                candidates = sorted(
                    candidates,
                    key=lambda r: (-(confidence_rank(r[6], r[7]) + bridge_bonus(r[0], theme, pattern)), r[0])
                )
                bridge = candidates[0]

        next_step = None
        if archetype or theme or pattern:
            ns_parts = []
            ns_params = []
            if archetype:
                ns_parts.append('n.used_for_archetype = ?')
                ns_params.append(archetype)
            if theme:
                ns_parts.append('n.used_for_theme = ?')
                ns_params.append(theme)
            if pattern:
                ns_parts.append('n.used_for_pattern = ?')
                ns_params.append(pattern)
            ns_where = ' OR '.join(ns_parts) if ns_parts else '1=0'
            candidates = cur.execute(f'''
                SELECT n.step_name, n.step_text, n.difficulty, n.time_horizon,
                       ct.confidence_level, ct.curation_level
                FROM next_step_library n
                LEFT JOIN confidence_tags ct ON ct.entity_type='next_step' AND ct.entity_id=n.id
                WHERE {ns_where}
            ''', ns_params).fetchall()
            if candidates:
                candidates = sorted(
                    candidates,
                    key=lambda r: (-(confidence_rank(r[4], r[5]) + next_step_bonus(r[0], theme, pattern, archetype)), r[0])
                )
                next_step = candidates[0]

        quote_pack = None
        anti_patterns = []
        case_links = []
        intervention_links = []
        motif_links = []
        source_strength = []
        if archetype:
            row = cur.execute(
                'SELECT r.pack_name, r.route_name, r.preferred_sources, r.preferred_quote_types '
                'FROM archetype_quote_packs a JOIN route_quote_packs r ON a.pack_id = r.id '
                'WHERE a.archetype_name = ? LIMIT 1',
                (archetype,),
            ).fetchone()
            if row:
                quote_pack = {
                    'pack_name': row[0],
                    'route_name': row[1],
                    'preferred_sources': row[2],
                    'preferred_quote_types': row[3],
                }
            anti_patterns = cur.execute(
                'SELECT anti_pattern_name FROM archetype_anti_patterns WHERE archetype_name = ?',
                (archetype,),
            ).fetchall()
            case_links = cur.execute(
                'SELECT c.case_name FROM case_archetypes a '
                'JOIN cases c ON a.case_id = c.id '
                'LEFT JOIN confidence_tags ct ON ct.entity_type = \'case\' AND ct.entity_id = c.id '
                'WHERE a.archetype_name = ? '
                'ORDER BY (ct.confidence_level IS NULL), '
                'CASE ct.confidence_level '
                "WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC "
                'LIMIT 3',
                (archetype,),
            ).fetchall()
            intervention_links = cur.execute(
                'SELECT intervention_pattern_name FROM archetype_interventions WHERE archetype_name = ? LIMIT 3',
                (archetype,),
            ).fetchall()
            source_strength = cur.execute(
                'SELECT source_name, strength FROM source_route_strength WHERE route_name = ? ORDER BY strength DESC LIMIT 3',
                (archetype,),
            ).fetchall()

        if archetype in {'shame-self-contempt', 'career-vocation', 'relationship-maintenance'}:
            motif_links = cur.execute(
                "SELECT DISTINCT s.motif_name FROM motif_cases m "
                "JOIN symbolic_motifs s ON m.motif_id = s.id "
                "JOIN case_archetypes a ON m.case_id = a.case_id "
                "WHERE a.archetype_name = ? LIMIT 3",
                (archetype,),
            ).fetchall()

        symbolic_permission = False
        if archetype in {'career-vocation', 'shame-self-contempt'} and motif_links:
            symbolic_permission = True

        confidence = []
        relevant_entity_ids = set()
        if bridge:
            brow = cur.execute(
                'SELECT id FROM bridge_to_action_templates WHERE template_name=?',
                (bridge[0],),
            ).fetchone()
            if brow:
                relevant_entity_ids.add(('bridge', brow[0]))
        if next_step:
            srow = cur.execute(
                'SELECT id FROM next_step_library WHERE step_name=?',
                (next_step[0],),
            ).fetchone()
            if srow:
                relevant_entity_ids.add(('next_step', srow[0]))
        if relevant_entity_ids:
            for etype, eid in relevant_entity_ids:
                for row in cur.execute(
                    'SELECT entity_type, entity_id, confidence_level, curation_level '
                    'FROM confidence_tags WHERE entity_type=? AND entity_id=?',
                    (etype, eid),
                ):
                    confidence.append(row)

        confidence_summary = {
            'bridge_confidence': None,
            'next_step_confidence': None,
        }
        if bridge:
            row = cur.execute(
                "SELECT confidence_level, curation_level FROM confidence_tags "
                "WHERE entity_type='bridge' AND entity_id=(SELECT id FROM bridge_to_action_templates WHERE template_name=?)",
                (bridge[0],),
            ).fetchone()
            if row:
                confidence_summary['bridge_confidence'] = {'confidence_level': row[0], 'curation_level': row[1]}
        if next_step:
            row = cur.execute(
                "SELECT confidence_level, curation_level FROM confidence_tags "
                "WHERE entity_type='next_step' AND entity_id=(SELECT id FROM next_step_library WHERE step_name=?)",
                (next_step[0],),
            ).fetchone()
            if row:
                confidence_summary['next_step_confidence'] = {'confidence_level': row[0], 'curation_level': row[1]}

        best_case = None
        if case_links:
            for case_name_tuple in case_links:
                case_name = case_name_tuple[0]
                row = cur.execute(
                    "SELECT c.id, ct.confidence_level, ct.curation_level "
                    "FROM cases c LEFT JOIN confidence_tags ct ON ct.entity_type='case' AND ct.entity_id=c.id "
                    "WHERE c.case_name=?",
                    (case_name,),
                ).fetchone()
                if row:
                    best_case = {
                        'case_id': row[0],
                        'case_name': case_name,
                        'confidence_level': row[1],
                        'curation_level': row[2],
                    }
                    break

        out = {
            'bridge': {
                'template_name': bridge[0],
                'diagnosis_stub': bridge[1],
                'responsibility_stub': bridge[2],
                'next_step_stub': bridge[3],
                'long_term_stub': bridge[4],
                'tone_profile': bridge[5],
                'confidence_level': bridge[6],
                'curation_level': bridge[7],
            } if bridge else None,
            'next_step': {
                'step_name': next_step[0],
                'step_text': next_step[1],
                'difficulty': next_step[2],
                'time_horizon': next_step[3],
                'confidence_level': next_step[4],
                'curation_level': next_step[5],
            } if next_step else None,
            'quote_pack': quote_pack,
            'anti_patterns': [r[0] for r in anti_patterns],
            'case_links': [r[0] for r in case_links],
            'best_case': best_case,
            'intervention_links': [r[0] for r in intervention_links],
            'motif_links': [r[0] for r in motif_links],
            'source_strength': [{'source_name': r[0], 'strength': r[1]} for r in source_strength],
            'symbolic_permission': symbolic_permission,
            'confidence_preview': confidence[:8],
            'confidence_summary': confidence_summary,
        }
    return out
