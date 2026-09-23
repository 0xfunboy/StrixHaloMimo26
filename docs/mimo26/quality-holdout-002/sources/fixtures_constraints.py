"""Six structurally new bounded problems: resource bundles, ordered routes, slot assignment."""
from __future__ import annotations
from fixture_utils import A,I,O,S,U,package
from solvers import verified_oracle


def selection_schema():return O(status=S,ids=A(S),cost=U('integer','null'),risk=U('integer','null'),value=U('integer','null'))
def route_schema():return O(status=S,path=A(S),cost=U('integer','null'),risk=U('integer','null'),time=U('integer','null'))
def assignment_schema():return O(status=S,assignments=A(O(job=S,worker=S,slot=I)),cost=U('integer','null'),makespan=U('integer','null'))


def resource_spec(rows,**kw):
    fields=('id','group','cost','risk','value','north_mb','south_mb')
    return {'kind':'selection','items':[dict(zip(fields,row)) for row in rows],**kw}


def route_spec(rows,**kw):
    return {'kind':'route','edges':[dict(zip(('from','to','cost','risk','time'),r)) for r in rows],**kw}


def make_constraints():
    cases=[]
    s1=resource_spec([
      ('M01','power',4,1,8,2,0),('M02','power',4,1,8,0,2),('M03','network',3,1,6,3,0),('M04','network',3,1,6,0,3),
      ('M05','storage',4,2,8,3,3),('M06','storage',5,1,8,2,2),('M07','audit',2,0,4,1,0),('M08','audit',2,0,4,0,1),
      ('M09','backup',3,1,5,1,2),('M10','backup',2,2,5,2,1)],budget=16,risk_max=5,count_min=5,count_max=6,
      groups={'power':[1,1],'network':[1,1],'storage':[1,1],'audit':[1,1],'backup':[0,1]},
      capacities={'north_mb':12,'south_mb':12},requires=[['M03','M01'],['M04','M02']],excludes=[['M07','M10'],['M08','M09']],coverage={'durable':['M05','M06']})
    text='''Scegli un sottoinsieme dei moduli, ciascuno zero o una volta. Non è consentito frazionare un modulo o sostituire un requisito con una capacità di un altro gruppo. cost è un costo intero in crediti, risk un punteggio intero additivo e value il beneficio intero additivo; north_mb e south_mb sono consumi separati e non trasferibili. budget e risk_max sono limiti inclusivi. count_min/count_max sono il numero minimo e massimo di moduli. Per ogni group, la coppia [min,max] è un vincolo distinto. Ogni coverage richiede almeno uno degli ID elencati. La relazione requires [a,b] significa che scegliere a obbliga a scegliere b, ma non viceversa. Ogni coppia excludes vieta di sceglierli entrambi. Gli ID rimangono stringhe esatte.
L’obiettivo è, nell’ordine: MASSIMIZZARE la somma value; poi MINIMIZZARE risk; poi MINIMIZZARE cost; infine scegliere la lista di ID ordinata lessicograficamente più piccola. Gli obiettivi sono gerarchici, non una somma pesata. Non sacrificare valore per ridurre rischio se il rischio è già ammissibile; applica lo spareggio solo a valori uguali. Tutti i vincoli restano obbligatori, indipendentemente dalla posizione nell’obiettivo. I gruppi simmetrici rappresentano interfacce diverse: le dipendenze devono comunque essere controllate.
Restituisci status OPTIMAL, ids ordinati crescenti e totali esatti cost/risk/value se esiste una soluzione. Se nessuna selezione è ammissibile, usa status INFEASIBLE, ids vuoto e tutti e tre i totali null. Non restituire una scelta parziale, non introdurre moduli non elencati, non indicare più alternative. Una proposta ammissibile ma non ottima non soddisfa il compito. Il risultato è soltanto un piano simulato: non abilita moduli o prenota memoria reale.'''
    cases.append(('CONSTRAINT-01','it','Composizione di moduli con gruppi, dipendenze e capacità distinte',s1,text,selection_schema(),1024))
    s2=resource_spec([
      ('P1','parse',3,1,7,4,0),('P2','parse',3,1,7,0,4),('N1','normalize',3,2,8,3,0),('N2','normalize',4,1,8,0,3),
      ('S1','sink',4,1,9,0,4),('S2','sink',3,2,9,4,0),('O1','observe',2,0,3,1,1),('O2','observe',1,1,3,1,1),('O3','observe',3,0,4,2,2)],
      budget=12,risk_max=6,count_min=3,count_max=4,groups={'parse':[1,1],'normalize':[1,1],'sink':[1,1],'observe':[0,1]},
      capacities={'north_mb':8,'south_mb':8},requires=[['S1','P1'],['S2','P2']],excludes=[['N1','O2'],['N2','O3']],coverage={'format-A':['P1','N2'],'format-B':['P2','N1']})
    text='''Choose binary software bundles for a synthetic two-zone pipeline. Every bundle is indivisible and can be selected at most once. cost, risk and value are additive integer quantities. north_mb and south_mb consume separate zone capacities; unused memory in one zone cannot compensate for overuse in the other. Group bounds [minimum,maximum] are inclusive. Both named coverage conditions must be satisfied by selecting at least one ID from each listed set. A single selected bundle may satisfy multiple conditions when its ID appears in them. requires [a,b] is one-way: selecting a requires b. excludes [a,b] means they cannot both be selected. The overall count, cost, risk and both memory limits all apply at once.
Optimization order is lexicographic: maximize total value, then minimize total risk, then minimize total cost, then choose the lexicographically smallest sorted ID list. Do not invent a score combining those priorities. A lower cost cannot compensate for worse risk when value is tied. Coverage and dependencies are hard constraints, not soft objectives. These rules intentionally mean that individually attractive bundles can be unusable together. Do not add the values of bundles that were not selected.
Return exactly one plan. When feasible, status is OPTIMAL and the response gives sorted ids and the recalculated integer cost/risk/value. When no feasible plan exists, return INFEASIBLE, an empty ids list and null totals. The resource model includes only the rows supplied; do not infer a default parser, zero-cost dependency, or external storage service. A feasible but suboptimal answer fails the objective, while a falsely claimed total fails arithmetic even if the ID choice is good. This fixture describes a plan only; no actual installation, deployment or allocation is requested.'''
    cases.append(('CONSTRAINT-02','en','Coverage-constrained two-zone pipeline selection',s2,text,selection_schema(),512))
    p1=route_spec([
      ('S','A',3,1,2),('S','B',2,1,2),('A','P',1,0,2),('B','P',2,0,2),('P','C',2,1,2),('P','D',2,0,2),
      ('C','Q',1,0,1),('D','Q',1,0,3),('Q','T',2,0,2),('D','T',1,0,1),('S','Q',1,0,1),('P','T',1,0,1),('B','C',1,0,1),('C','D',1,0,1)],
      start='S',end='T',required=['P','Q'],precedence=[['P','Q']],forbidden=[],limits={'cost':12,'risk':4,'time':12},max_edges=6,objective=['cost','risk','time'])
    text='''Trova un percorso semplice da S a T nel grafo DIRETTO. Le righe sono gli unici archi esistenti: da un arco a->b non deriva b->a. Non ripetere vertici. Il percorso deve visitare entrambi P e Q, con P prima di Q. Ogni limite è inclusivo e si applica alla somma degli archi; max_edges conta gli archi, non i vertici. cost è in crediti interi, risk in punti interi, time in minuti interi. Non ci sono costi di attesa, servizi ai nodi o penalità non elencate. Un arco breve che evita un checkpoint non rende ammissibile il percorso.
L’obiettivo, in questo ordine, è minimizzare cost, poi risk, poi time, infine scegliere la sequenza di vertici lessicograficamente più piccola. Il tie-break lessicografico confronta il primo vertice diverso, poi la lunghezza solo in caso di prefisso comune. La velocità non viene preferita a un rischio minore se il costo è uguale: rispetta l’ordine dei criteri. Non ordinare alfabeticamente il percorso prima di confrontarlo, perché la sequenza rappresenta la visita reale.
Restituisci status OPTIMAL, path comprensivo di S e T e i tre totali interi ricalcolati dagli archi scelti. Se nessun percorso rispetta tutti i vincoli, restituisci INFEASIBLE, path vuoto e cost/risk/time null. Non presentare una rotta parziale o una seconda rotta di riserva. I vertici non visitati non contribuiscono ai totali. Le limitazioni riguardano soltanto questa simulazione: l’output non è un comando a un veicolo. È essenziale distinguere costo dichiarato, costo effettivo e obiettivo ottimale; nessuno di questi valori può essere inferito dal numero di tappe.'''
    cases.append(('CONSTRAINT-03','it','Percorso con checkpoint ordinati e priorità costo-rischio-tempo',p1,text,route_schema(),512))
    p2=route_spec([
      ('U','H',2,0,2),('U','J',1,1,1),('H','K',2,0,3),('J','K',2,0,2),('H','L',1,0,1),('L','K',1,0,2),
      ('K','M',3,1,3),('K','N',2,0,2),('N','M',2,0,2),('M','Z',2,0,2),('N','Z',1,0,1),('K','X',1,0,1),('X','M',1,0,1),('M','L',1,0,1)],
      start='U',end='Z',required=['K','M'],precedence=[['K','M']],forbidden=['X'],limits={'cost':14,'risk':3,'time':14},max_edges=6,objective=['risk','time','cost'])
    text='''Find a simple directed route from U to Z. All and only the listed directed edges exist. A vertex may not be repeated and X is forbidden even if an edge through it looks cheaper. Both K and M must occur, with K before M. The route has at most max_edges edges and must obey every inclusive cost, risk and time limit. Costs are integer credits, risk is an additive integer score, time is additive integer minutes. There are no implicit reverse edges, free transitions, waiting actions, or node-service costs.
The objective order is deliberately different from a cheapest-path problem: minimize risk first, then time, then cost, then the lexicographically smallest vertex sequence. Never trade additional risk for a faster or cheaper route when a lower-risk feasible route exists. Lexicographic comparison applies to the actual sequence beginning at U, not a sorted vertex set. A longer sequence can precede another sequence if its first differing vertex sorts earlier; length only resolves a true prefix tie.
Return status OPTIMAL, the full path including endpoints, and exact integer totals. If no permitted route exists, return status INFEASIBLE, an empty path and null cost/risk/time. The direct edge from N to Z is available but does not waive the M checkpoint. A cycle involving L is not allowed simply because its individual edges exist. The schema permits no prose rationale or alternative routes. Totals must come from the chosen edges rather than an unconstrained route used during reasoning. This is synthetic routing data, not an instruction to operate a network or transport system.'''
    cases.append(('CONSTRAINT-04','en','Risk-first route with a forbidden vertex and ordered coverage',p2,text,route_schema(),512))
    a1={'kind':'assignment','workers':[{'id':'W-A','slots':[0,1,2]},{'id':'W-B','slots':[0,1,2]}],
      'jobs':[{'id':'J1','eligible':['W-A','W-B'],'slots':[0,1],'cost':{'W-A':2,'W-B':3},'role':'setup'},
              {'id':'J2','eligible':['W-A','W-B'],'slots':[0,1],'cost':{'W-A':2,'W-B':2},'role':'input verification'},
              {'id':'J3','eligible':['W-B'],'slots':[1,2],'cost':{'W-A':99,'W-B':2},'role':'specialist verification'},
              {'id':'J4','eligible':['W-A','W-B'],'slots':[1,2],'cost':{'W-A':3,'W-B':1},'role':'packaging audit'},
              {'id':'J5','eligible':['W-A'],'slots':[1,2],'cost':{'W-A':2,'W-B':99},'role':'release preparation'}],
      'precedence':[['J1','J3'],['J2','J5']],'different_slot':[['J3','J4']],'budget':12}
    text='''Assegna ogni job una sola volta a un worker e a uno slot intero. Ogni job dura esattamente uno slot: inizia a slot e termina a slot+1. Ogni worker può svolgere al massimo un job per slot. Il job deve ammettere sia il worker sia lo slot nella propria scheda, e il worker deve essere disponibile nello slot. I valori cost per worker non ammessi sono conservati nel catalogo ma NON concedono eleggibilità: pagare 99 non rende valida una coppia vietata.
Per una precedenza [a,b], a deve finire non dopo l’inizio di b; con durate unitarie ciò significa slot(a)<slot(b), indipendentemente dai worker. different_slot vieta due job nello stesso slot anche su worker diversi. budget limita la somma dei costi assegnati ed è inclusivo. Non sono ammessi job omessi, duplicati, spezzati o eseguiti fuori dagli slot elencati.
Minimizza prima il costo totale, poi makespan=max(slot+1), infine la sequenza di coppie (worker,slot) ottenuta ordinando i job per id. Per il tie-break worker si confronta come stringa lessicografica e slot come intero; si confronta la prima coppia diversa nella sequenza. Questo non è un criterio di minimizzazione separata per ogni job: tutti i vincoli globali devono restare rispettati. Makespan è un tempo finale assoluto, non il numero di job.
Se esiste un’assegnazione valida, restituisci OPTIMAL, assignments ordinata per job id e i totali cost/makespan interi. Se non esiste, restituisci INFEASIBLE, assignments vuoto e cost/makespan null. Una dichiarazione di impossibilità deve riguardare tutti i piani, non soltanto una scelta greedy fallita. Non fornire codice o strumenti per la ricerca. Questa è una pianificazione simulata, non un’assegnazione reale di turni.'''
    cases.append(('CONSTRAINT-05','it','Assegnazione con competenze, precedenze, risorsa esclusiva e tie-break',a1,text,assignment_schema(),1024))
    a2={'kind':'assignment','workers':[{'id':'W-A','slots':[0,1,2]},{'id':'W-B','slots':[0,1,2]}],
      'jobs':[{'id':'A','eligible':['W-A','W-B'],'slots':[0,1],'cost':{'W-A':2,'W-B':2},'role':'batch registration'},
              {'id':'B','eligible':['W-A'],'slots':[1,2],'cost':{'W-A':2,'W-B':99},'role':'sealed-unit certification'},
              {'id':'C','eligible':['W-A'],'slots':[1,2],'cost':{'W-A':2,'W-B':99},'role':'pressure-unit certification'},
              {'id':'D','eligible':['W-A'],'slots':[1,2],'cost':{'W-A':2,'W-B':99},'role':'electrical-unit certification'},
              {'id':'E','eligible':['W-B'],'slots':[0,2],'cost':{'W-A':99,'W-B':1},'role':'packing register'}],
      'precedence':[['A','B'],['A','C']],'different_slot':[['C','E']],'budget':12}
    text='''Assign every job exactly once. Each job occupies one entire integer slot and finishes at slot+1. Each worker can process at most one job in a slot. Eligibility and job slot domains are mandatory; an explicit cost for a noneligible worker is catalog information only and does not authorize that assignment. The worker must also list that slot as available. Do not create overtime, split jobs, reuse a worker simultaneously, or leave required work unassigned.
A precedence [a,b] means a finishes before or at b’s start, which is slot(a)<slot(b) for unit-length jobs. A different_slot pair forbids simultaneity even on different workers. All jobs are mandatory, with no optional status or partial-service credit. Total assignment cost must not exceed the inclusive budget. Cost entries of 99 do not override eligibility; increasing budget would not remove a skill constraint.
Find the globally minimum cost feasible plan, then minimum makespan, then the lexicographically smallest list of (worker,slot) pairs in job-id order. Worker names are compared lexicographically, slot numbers numerically. Makespan is max(slot+1). The objectives matter only among feasible plans; a low-cost incomplete schedule is not a feasible alternative.
If a feasible plan exists, return OPTIMAL with all assignments sorted by job id and exact totals. If no complete plan is feasible, return INFEASIBLE with assignments=[] and both totals null. Do not force a schedule merely because total capacity across all workers exceeds the number of jobs: compatible worker-slot combinations also matter. Conversely, a failed first attempt alone does not prove impossibility. The response is only data; no job is actually scheduled. All resources and restrictions are in this fixture and no hidden worker or external contractor may be assumed.'''
    cases.append(('CONSTRAINT-06','en','Mandatory specialist jobs with restricted worker-slot compatibility',a2,text,assignment_schema(),512))
    out=[]
    for cid,lang,title,spec,text,schema,cap in cases:
        expected,proof,feasible=verified_oracle(spec)
        c,e=package(cid,'CONSTRAINT',lang,title,text,spec,expected,schema,cap,spec=spec,oracle_proof=proof,feasible_solutions=feasible,critical_rule='')
        out.append((c,e))
    assert sum(e['expected']['status']=='INFEASIBLE' for c,e in out)>=1
    assert sum(e['oracle_proof']['primary']['primary_objective_ties']>1 for c,e in out)>=2
    return out
