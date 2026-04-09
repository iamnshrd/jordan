"""User-reaction estimation.

Refactored from: estimate_user_reaction.
"""
from library.config import CHECKPOINTS, REACTION_ESTIMATE
from library.utils import load_checkpoints, save_json


def estimate(question=''):
    """Estimate user reaction from recent checkpoints.

    Writes user_reaction_estimate.json and returns the result dict.
    """
    rows = load_checkpoints(CHECKPOINTS)

    if question:
        recent = [r for r in rows if r.get('question') == question][-3:]
    else:
        recent = rows[-3:]

    if not recent:
        result = {'question': question, 'user_reaction_estimate': 'unknown'}
    else:
        if any(r.get('movement_estimate') == 'moving' for r in recent):
            reaction = 'accepting'
        elif all(r.get('movement_estimate') == 'stuck' for r in recent):
            reaction = 'resisting'
        else:
            reaction = 'ambiguous'
        result = {'question': question, 'user_reaction_estimate': reaction}

    save_json(REACTION_ESTIMATE, result)
    return result
