"""Assemble the 18-case, 9IT/9EN synthetic holdout. No model output is read."""
from collections import Counter
from fixtures_json import make_json
from fixtures_evidence import make_evidence
from fixtures_constraints import make_constraints


def make_panel():
    rows=make_json()+make_evidence()+make_constraints()
    cases=[c for c,e in rows];expected=[e for c,e in rows]
    assert len(rows)==18 and len({c['case_id'] for c in cases})==18
    assert Counter(c['language'] for c in cases)=={'it':9,'en':9}
    for family in ('JSON','EVIDENCE','CONSTRAINT'):
        group=[c for c in cases if c['family']==family]
        assert len(group)==6
        assert Counter(c['language'] for c in group)=={'it':3,'en':3}
        assert Counter(c['output_cap'] for c in group)=={512:4,1024:2}
    assert sum(c['output_cap'] for c in cases)==12288
    return cases,expected
