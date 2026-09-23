"""Exact bounded CPU oracles; never imported by model workers.
Primary enumeration and independent search have distinct feasibility implementations.
"""
from __future__ import annotations
import itertools


def key(spec, v):
    kind=spec['kind']
    if kind=='selection':return (-v['value'],v['risk'],v['cost'],tuple(v['ids']))
    if kind=='route':
        vals={'cost':v['cost'],'risk':v['risk'],'time':v['time']}
        return tuple(vals[x] for x in spec['objective'])+(tuple(v['path']),)
    return (v['cost'],v['makespan'],tuple((x['worker'],x['slot']) for x in v['assignments']))


def assess(spec, v):
    """Recalculate only from supplied decisions and fixture data, never repair v."""
    errors=[];kind=spec['kind'];out=None
    if kind=='selection':
        ids=v.get('ids',[]);catalog={x['id']:x for x in spec['items']}
        if len(set(ids))!=len(ids):errors.append('duplicate selected ID')
        if any(x not in catalog for x in ids):return None,['unknown selected ID']
        rows=[catalog[x] for x in ids];chosen=set(ids)
        cost=sum(x['cost'] for x in rows);risk=sum(x['risk'] for x in rows);val=sum(x['value'] for x in rows)
        if cost>spec['budget']:errors.append(f'cost {cost} > budget {spec["budget"]}')
        if risk>spec['risk_max']:errors.append(f'risk {risk} > maximum {spec["risk_max"]}')
        if not spec['count_min']<=len(ids)<=spec['count_max']:errors.append('selected count outside allowed interval')
        for g,limits in spec['groups'].items():
            n=sum(x['group']==g for x in rows)
            if not limits[0]<=n<=limits[1]:errors.append(f'group {g}: {n} outside {limits}')
        for cap,limit in spec.get('capacities',{}).items():
            used=sum(x.get(cap,0) for x in rows)
            if used>limit:errors.append(f'capacity {cap}: {used} > {limit}')
        for a,b in spec['requires']:
            if a in chosen and b not in chosen:errors.append(f'{a} requires {b}')
        for a,b in spec['excludes']:
            if {a,b}<=chosen:errors.append(f'incompatible {a}/{b}')
        for name,acceptable in spec.get('coverage',{}).items():
            if not chosen.intersection(acceptable):errors.append(f'missing coverage {name}')
        out={'status':'OPTIMAL','ids':sorted(ids),'cost':cost,'risk':risk,'value':val}
    elif kind=='route':
        path=v.get('path',[]);edges={(e['from'],e['to']):e for e in spec['edges']}
        if not path or path[0]!=spec['start'] or path[-1]!=spec['end']:errors.append('wrong route endpoints')
        if len(path)!=len(set(path)):errors.append('repeated route vertex')
        if any(x in spec.get('forbidden',[]) for x in path):errors.append('forbidden vertex used')
        for node in spec['required']:
            if node not in path:errors.append('missing waypoint '+node)
        for a,b in spec['precedence']:
            if a not in path or b not in path or path.index(a)>=path.index(b):errors.append(f'waypoint order {a} before {b} violated')
        missing=[a+'->'+b for a,b in zip(path,path[1:]) if (a,b) not in edges]
        if missing:return None,errors+['nonexistent edge '+x for x in missing]
        used=[edges[a,b] for a,b in zip(path,path[1:])]
        sums={k:sum(e[k] for e in used) for k in ('cost','risk','time')}
        for name,maximum in spec['limits'].items():
            if sums[name]>maximum:errors.append(f'{name} {sums[name]} > limit {maximum}')
        if len(used)>spec['max_edges']:errors.append('too many route edges')
        out={'status':'OPTIMAL','path':path,**sums}
    else:
        rows=v.get('assignments',[]);jobs={j['id']:j for j in spec['jobs']};workers={w['id']:w for w in spec['workers']}
        if len(rows)!=len(jobs) or {x['job'] for x in rows}!=set(jobs):errors.append('each job must occur exactly once')
        if any(x['job'] not in jobs or x['worker'] not in workers for x in rows):return None,errors+['unknown job/worker']
        byjob={x['job']:x for x in rows};occupied=set();cost=0
        for x in rows:
            j=jobs[x['job']];w=workers[x['worker']];slot=x['slot']
            if (x['worker'],slot) in occupied:errors.append(f'double booking {x["worker"]} slot {slot}')
            occupied.add((x['worker'],slot))
            if x['worker'] not in j['eligible']:errors.append(f'{x["job"]}: worker not eligible')
            if slot not in j['slots'] or slot not in w['slots']:errors.append(f'{x["job"]}: unavailable slot {slot}')
            cost+=j['cost'][x['worker']]
        for a,b in spec['precedence']:
            if a not in byjob or b not in byjob or byjob[a]['slot']>=byjob[b]['slot']:errors.append(f'{a} must finish before {b}')
        for a,b in spec['different_slot']:
            if a in byjob and b in byjob and byjob[a]['slot']==byjob[b]['slot']:errors.append(f'{a}/{b}: same slot forbidden')
        if cost>spec['budget']:errors.append(f'cost {cost} > budget {spec["budget"]}')
        makespan=max([x['slot']+1 for x in rows],default=0)
        out={'status':'OPTIMAL','assignments':sorted(rows,key=lambda x:x['job']),'cost':cost,'makespan':makespan}
    return out,errors


def primary(spec):
    """Full finite enumeration; all feasible outcomes retained for pre-GPU audit."""
    feasible=[];kind=spec['kind'];visited=0
    if kind=='selection':
        it=({'ids':[r['id'] for i,r in enumerate(spec['items']) if mask>>i&1]} for mask in range(1<<len(spec['items'])))
    elif kind=='route':
        mids=sorted({e[k] for e in spec['edges'] for k in ('from','to')}-{spec['start'],spec['end']})
        it=({'path':[spec['start'],*p,spec['end']]} for n in range(len(mids)+1) for p in itertools.permutations(mids,n))
    else:
        jobs=sorted(spec['jobs'],key=lambda j:j['id'])
        domains=[[(w,s) for w in sorted(j['eligible']) for s in sorted(j['slots'])] for j in jobs]
        it=({'assignments':[{'job':j['id'],'worker':w,'slot':s} for j,(w,s) in zip(jobs,choices)]} for choices in itertools.product(*domains))
    for candidate in it:
        visited+=1
        if visited>250000:raise ValueError('exact search budget exceeded')
        computed,errors=assess(spec,candidate)
        if not errors:feasible.append(computed)
    feasible.sort(key=lambda v:key(spec,v))
    if not feasible:
        empty={'status':'INFEASIBLE'}
        if kind=='selection':empty.update(ids=[],cost=None,risk=None,value=None)
        elif kind=='route':empty.update(path=[],cost=None,risk=None,time=None)
        else:empty.update(assignments=[],cost=None,makespan=None)
        return empty,{'enumerated':visited,'feasible_count':0,'primary_objective_ties':0},[]
    objective=key(spec,feasible[0])[0]
    return feasible[0],{'enumerated':visited,'feasible_count':len(feasible),'primary_objective_ties':sum(key(spec,x)[0]==objective for x in feasible)},feasible


def independent(spec):
    """Independent feasibility and accumulated arithmetic; no assess()/primary()."""
    kind=spec['kind'];solutions=[];visits=0
    if kind=='selection':
        rows=spec['items']
        def walk(i,chosen,cost,risk,value,caps,groups):
            nonlocal visits
            visits+=1
            if cost>spec['budget'] or risk>spec['risk_max'] or len(chosen)>spec['count_max']:return
            if i<len(rows):
                r=rows[i]
                walk(i+1,chosen,cost,risk,value,caps,groups)
                walk(i+1,chosen+[r['id']],cost+r['cost'],risk+r['risk'],value+r['value'],
                     {k:caps.get(k,0)+r.get(k,0) for k in spec.get('capacities',{})},
                     {**groups,r['group']:groups.get(r['group'],0)+1})
                return
            selected=set(chosen)
            if len(chosen)<spec['count_min']:return
            if any(not lo<=groups.get(g,0)<=hi for g,(lo,hi) in spec['groups'].items()):return
            if any(caps.get(k,0)>limit for k,limit in spec.get('capacities',{}).items()):return
            if any(a in selected and b not in selected for a,b in spec['requires']):return
            if any(a in selected and b in selected for a,b in spec['excludes']):return
            if any(not any(x in selected for x in choices) for choices in spec.get('coverage',{}).values()):return
            solutions.append({'status':'OPTIMAL','ids':sorted(chosen),'cost':cost,'risk':risk,'value':value})
        walk(0,[],0,0,0,{}, {})
        rank=lambda x:(-x['value'],x['risk'],x['cost'],tuple(x['ids']))
    elif kind=='route':
        adjacency={}
        for e in spec['edges']:adjacency.setdefault(e['from'],[]).append(e)
        def walk(node,path,cost,risk,elapsed):
            nonlocal visits
            visits+=1
            totals={'cost':cost,'risk':risk,'time':elapsed}
            if len(path)-1>spec['max_edges'] or any(totals[k]>n for k,n in spec['limits'].items()):return
            if node==spec['end']:
                if any(n not in path for n in spec['required']):return
                positions={n:i for i,n in enumerate(path)}
                if any(a not in positions or b not in positions or positions[a]>=positions[b] for a,b in spec['precedence']):return
                solutions.append({'status':'OPTIMAL','path':path,'cost':cost,'risk':risk,'time':elapsed});return
            for e in adjacency.get(node,[]):
                if e['to'] in path or e['to'] in spec.get('forbidden',[]):continue
                walk(e['to'],path+[e['to']],cost+e['cost'],risk+e['risk'],elapsed+e['time'])
        walk(spec['start'],[spec['start']],0,0,0)
        rank=lambda x:tuple(x[k] for k in spec['objective'])+(tuple(x['path']),)
    else:
        # Most constrained job first, vs lexicographic full product in primary.
        jobs=sorted(spec['jobs'],key=lambda j:(len(j['eligible'])*len(j['slots']),j['id']))
        availability={w['id']:set(w['slots']) for w in spec['workers']}
        def walk(i,allocated,occupied,cost):
            nonlocal visits
            visits+=1
            if cost>spec['budget']:return
            if i==len(jobs):
                rows=[{'job':k,'worker':w,'slot':s} for k,(w,s) in sorted(allocated.items())]
                solutions.append({'status':'OPTIMAL','assignments':rows,'cost':cost,'makespan':max(s+1 for w,s in allocated.values())});return
            j=jobs[i]
            for w in j['eligible']:
                for s in j['slots']:
                    if s not in availability[w] or (w,s) in occupied:continue
                    new={**allocated,j['id']:(w,s)}
                    if any(a in new and b in new and new[a][1]>=new[b][1] for a,b in spec['precedence']):continue
                    if any(a in new and b in new and new[a][1]==new[b][1] for a,b in spec['different_slot']):continue
                    walk(i+1,new,occupied|{(w,s)},cost+j['cost'][w])
        walk(0,{},set(),0)
        rank=lambda x:(x['cost'],x['makespan'],tuple((r['worker'],r['slot']) for r in x['assignments']))
    if visits>250000:raise ValueError('independent search budget exceeded')
    return (min(solutions,key=rank) if solutions else None),{'search_nodes':visits,'feasible_count':len(solutions)}


def verified_oracle(spec):
    a,proof,feasible=primary(spec);b,proof2=independent(spec)
    assert (a['status']=='INFEASIBLE' and b is None) or a==b,'INDEPENDENT_ORACLE_DISAGREEMENT'
    assert proof['feasible_count']==proof2['feasible_count'],'INDEPENDENT_FEASIBILITY_COUNT_DISAGREEMENT'
    return a,{'primary':proof,'independent':proof2,'agreement':True},feasible
