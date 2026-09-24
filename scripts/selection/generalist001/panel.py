"""Twelve new synthetic selection tasks; solutions never enter public cases."""
from __future__ import annotations
import code_cases
import data_cases
import math_cases
import docs_cases
import science_cases
import ops_cases

FAMILIES=('CODE','DATA','MATH','DOCS','SCIENCE','OPS')


def cases():
    rows=code_cases.cases()+data_cases.cases()+math_cases.cases()+docs_cases.cases()+science_cases.cases()+ops_cases.cases()
    assert len(rows)==12 and len({x['case_id'] for x in rows})==12
    assert sum(x['output_cap'] for x in rows)==73728
    for family in FAMILIES:
        group=[x for x in rows if x['family']==family]
        assert len(group)==2 and {x['language'] for x in group}=={'it','en'}
    return rows


def sanity():
    return [
        {'case_id':'SANITY-arithmetic','name':'arithmetic','content':'Compute 17*19. Return only the integer.','output_cap':1024},
        {'case_id':'SANITY-extract','name':'extract','content':'Read this exact token: ZEBRA-4821. Return only that token.','output_cap':1024},
        {'case_id':'SANITY-json','name':'json','content':'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".','output_cap':1024},
        {'case_id':'SANITY-italian','name':'italian','content':'Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.','output_cap':1024},
        {'case_id':'SANITY-english','name':'english','content':'Alice is first and Bob is second. Who is second? Return only the name.','output_cap':1024},
        {'case_id':'SANITY-code_clamp','name':'code_clamp','content':'Return only Python code defining clamp(x, lo, hi). It must return lo when x < lo, hi when x > hi, otherwise x. Do not import anything and do not call other functions.','output_cap':1536},
    ]


def engine_document():
    intro='''Review this synthetic specification of a resumable object-processing service. Write a detailed technical critique longer than 128 tokens, examining correctness boundaries and the interactions among sections rather than copying the input. Do not call tools or perform operations. The document describes proposed invariants, not measurements or live cluster logs.\n\n'''
    topics=[
        ('Admission','Each accepted request obtains a durable request identifier before it is queued. Repeated submissions with the same identifier return the recorded result; a request whose receipt is missing is not presumed successful.'),
        ('Object versioning','An object version consists of immutable content bytes, a schema number and an origin signature. The storage path alone does not identify the version. Readers validate the bound hash before interpreting fields.'),
        ('Authorization','Permission receipts bind principal, action, object version and expiry. A test result is not a permission. A renewed permission does not retroactively authorize an action performed under an expired grant.'),
        ('Queue partitions','Partitions have increasing offsets with explicit gaps. The consumer tracks acknowledged offsets separately from materialized business effects. Offset acknowledgment cannot hide a missing output commit.'),
        ('Lease epochs','A lease identifies owner and epoch; its expiration stops new admission but does not prove that an old operation did not commit. Reconciliation reads the authoritative operation journal before reassignment.'),
        ('Temporary staging','Writes first produce immutable staging objects. Publishing a pointer requires all referenced objects and their receipts. An incomplete staging area remains visible as incomplete rather than being renamed final.'),
        ('Schema translation','Translations preserve absent fields separately from explicit null, zero, false and empty strings. Version precedence is numeric and is resolved before conversion. The original event is retained with the translated view.'),
        ('Deduplication','Only a validated accepted operation claims its idempotency key. A rejected operation cannot prevent a later valid retry. A duplicate valid operation is a no-op and must not overwrite the first immutable receipt.'),
        ('Rollback','Rollback changes the active pointer only after the old and new states are identified. It does not erase the failed operation or its initial cause. Dependencies still in use cannot be removed merely because rollback finished.'),
        ('Metrics','Every duration declares its observer and boundaries. Queue wait, prompt processing, output generation and response transport remain distinct. Unobserved timestamps are null and are not reconstructed from throughput ratios.'),
        ('Caching','Resident code and warmed allocation do not imply prior-request state reuse. Each request records processed and reused input counts. In-request working state is normal and is not mislabeled an inter-request cache hit.'),
        ('Memory accounting','Shared pages may appear in process mappings and device-visible allocations. Capacity planning records physical availability, private working sets and mapped files separately, without summing overlapping categories.'),
        ('Cancellation','Cancellation requests have their own durable receipts. If an operation finished before cancellation was applied, its completed result remains authoritative. A caller disconnect is not treated as proof of cancellation.'),
        ('Cross-node coordination','Each peer exposes boot identity, invocation identity and current epoch. A failed network read gives UNKNOWN, not OFF. Cleanup stops only owned invocations and cannot infer process identity from a generic executable name.'),
        ('Validation','Format checks precede semantic checks but never replace them. An internally consistent total can still describe the wrong records. Independent recalculation uses available source inputs rather than the candidate result as its oracle.'),
        ('Documents','Every claim has its own supporting record set. A real record identifier is insufficient when the record is irrelevant, superseded or outside the cutoff. Missing evidence must not be replaced with plausible text.'),
        ('Task graphs','A task can start only after all mandatory predecessor results are terminal and accepted. A successful sibling does not satisfy another predecessor. The planner validates resource conflicts separately from graph acyclicity.'),
        ('Partial completion','A request stopped at its output limit remains partial even when its text looks polished. No additional request silently completes it. The denominator includes partial and technically failed requests.'),
        ('Replication','A replica serving a different request increases capacity but does not accelerate one request. Sharding weights changes residency requirements; it does not guarantee lower latency or preserve a previous numerical path.'),
        ('Recovery handoff','The handoff records the last observed state, source revisions, current jobs and a single next action. Historical next actions in archived reports are not automatically reactivated by a new session.'),
    ]
    sections=[]
    for cycle in range(1,7):
        for index,(name,body) in enumerate(topics,1):
            variant=[
                'A coordinator crash may occur after the write but before the acknowledgment. Explain which durable evidence distinguishes committed, rejected and unknown outcomes.',
                'Consider a delayed peer response arriving after a newer epoch has been admitted. Identify the checks that prevent stale state from replacing the authoritative result.',
                'Examine a schema migration running while old readers remain active. State which fields must remain immutable and which compatibility decision must be explicit.',
                'Consider a timeout during cleanup with one peer unreachable. Identify safe read-only reconciliation steps and the evidence required before any state transition.',
                'Discuss an output that passes structural validation but violates a cross-record invariant. Explain what can be rejected at runtime and what still requires an independent computation.',
                'Assess a rolling deployment with concurrent requests and bounded storage. Describe how to preserve ownership, auditability and capacity without clearing global state.',
            ][cycle-1]
            sections.append(f'Section {cycle}.{index}: {name}. {body} {variant}\n')
    return intro,sections


def mtp_cases():
    # Fixed coverage before target outputs: no post-run prompt hunting.
    code='\n'.join(f'def transform_{i}(values):\n    return [x + {i} for x in values if x is not None]\n' for i in range(96))
    return [
        {'case_id':'MTP-PROSE-1','content':'Write a careful explanation of why an HTTP timeout does not prove that a database transaction rolled back. Include concrete distinctions between journal intent, durable commit and a delayed acknowledgment. Use more than 256 tokens.','output_cap':256},
        {'case_id':'MTP-PROSE-2','content':'Write an original, detailed technical discussion of scientific measurement uncertainty, correlated sensors and causal evidence. Do not provide a short checklist. Continue for more than 256 tokens.','output_cap':256},
        {'case_id':'MTP-CODE-1','content':'Write a complete Python implementation of a bounded event replay ledger with immutable receipts, input validation, typed outcomes and tests. Use only the standard library. Return code longer than 256 tokens.','output_cap':256},
        {'case_id':'MTP-CODE-2','content':'Write a complete Python parser for a small arithmetic language with parentheses, unary signs, multiplication and division. Include a tokenizer, syntax errors and tests. Return more than 256 tokens of code.','output_cap':256},
        {'case_id':'MTP-REWRITE-1','content':'Rewrite every function below. Rename the argument values to records, preserve the per-function numeric constant and replace the filter x is not None with isinstance(x, int). Return the full source, not a diff.\n'+code,'output_cap':256},
        {'case_id':'MTP-REWRITE-2','content':'Rewrite the full source below as a single dispatch function keyed by numeric function index. Preserve filtering and arithmetic exactly, add explicit validation for unknown indices, and include tests for negative and zero values. Return more than 256 tokens.\n'+code,'output_cap':256},
    ]
