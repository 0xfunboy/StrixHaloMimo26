"""New bounded optimization tasks; different exact formulations crosscheck references."""
from __future__ import annotations
import itertools
import json

ENERGY={'base':[2,1,3,1],'solar':[0,3,0,1],'price':[5,2,7,3], 'initial':1,'final':1,'capacity':3,'grid_limit':3,'power_limit':2,'job_load':2,'job_slots':[1,2]}
PRODUCTION={'resource1':[3,2,1],'resource2':[1,3,2],'labor':[2,1,2],'limit':[12,11,10],'scenario1':[2,1,2],'scenario2':[1,2,2],'minimum':[8,8],'profit':[11,9,8],'setup':[0,3,2]}


def energy_key(row):
    return row['cost'],sum(row['curtail']),row['job_slot'],tuple(row['battery_delta'])


def production_key(row):
    return -row['profit'],row['resource2'],sum(row['batches']),tuple(row['batches'])


def energy_assess(row):
    errors=[]
    if row['job_slot'] not in ENERGY['job_slots']:errors.append('job slot forbidden')
    if any(len(row[k])!=4 for k in ['battery_delta','grid','curtail','soc']):return None,['four slots required']
    level=1;levels=[];grid=[]
    for t,u in enumerate(row['battery_delta']):
        if not -2<=u<=2:errors.append('battery power slot '+str(t))
        level+=u;levels.append(level)
        if not 0<=level<=3:errors.append('battery capacity slot '+str(t))
        c=row['curtail'][t]
        if not 0<=c<=ENERGY['solar'][t]:errors.append('curtailment bounds slot '+str(t))
        g=ENERGY['base'][t]+(2 if t==row['job_slot'] else 0)+u-ENERGY['solar'][t]+c
        grid.append(g)
        if not 0<=g<=3:errors.append('grid bound slot '+str(t))
    if level!=1:errors.append('terminal charge')
    cost=sum(a*b for a,b in zip(grid,ENERGY['price']))
    calc={'job_slot':row['job_slot'],'battery_delta':row['battery_delta'],'grid':grid,'curtail':row['curtail'],'soc':levels,'cost':cost}
    return calc,errors


def production_assess(row):
    x=row['batches'];errors=[]
    if len(x)!=3:return None,['three batch counts required']
    if any(not 0<=n<=4 for n in x) or x[0]<1 or x[1]<1 or sum(x)>6:errors.append('batch bounds or total')
    vals={k:sum(a*b for a,b in zip(x,PRODUCTION[k])) for k in ['resource1','resource2','labor','scenario1','scenario2']}
    for key,lim in zip(['resource1','resource2','labor'],PRODUCTION['limit']):
        if vals[key]>lim:errors.append(key+' capacity')
    for key in ['scenario1','scenario2']:
        if vals[key]<8:errors.append(key+' guarantee')
    profit=sum(a*b for a,b in zip(x,PRODUCTION['profit']))-sum(s for n,s in zip(x,PRODUCTION['setup']) if n>0)
    return {'batches':x,**vals,'profit':profit},errors


def check_independent():
    # Formulation 1 enumerates signed battery transitions; formulation 2 searches
    # grid import and used solar recursively and derives the battery transition.
    first=[]
    for j in [1,2]:
        for u in itertools.product(range(-2,3),repeat=4):
            for c in itertools.product(*[range(s+1) for s in ENERGY['solar']]):
                calc,errors=energy_assess({'job_slot':j,'battery_delta':list(u),'grid':[0]*4,'curtail':list(c),'soc':[0]*4})
                if not errors:first.append(calc)
    second=[]
    def search(j,t,level,u,g,c,levels):
        if t==4:
            if level==1:second.append({'job_slot':j,'battery_delta':u,'grid':g,'curtail':c,'soc':levels,'cost':sum(g[i]*[5,2,7,3][i] for i in range(4))})
            return
        demand=[2,1,3,1][t]+(2 if t==j else 0)
        for imported in range(4):
            for used in range([0,3,0,1][t]+1):
                change=imported+used-demand;new=level+change
                if abs(change)<=2 and 0<=new<=3:
                    search(j,t+1,new,u+[change],g+[imported],c+[[0,3,0,1][t]-used],levels+[new])
    for j in [1,2]:search(j,0,1,[],[],[],[])
    assert len(first)==len(second)==150
    literal={'job_slot':1,'battery_delta':[-1,2,-2,1],'grid':[1,2,1,1],'curtail':[0,0,0,0],'soc':[0,2,0,1],'cost':19}
    assert min(first,key=energy_key)==min(second,key=energy_key)==literal
    feasible=[]
    for x in itertools.product(range(5),repeat=3):
        calc,errors=production_assess({'batches':list(x)})
        if not errors:feasible.append(calc)
    # A distinct total-batch parameterization derives C and codes constraints
    # directly rather than calling the first checker.
    independent=[]
    for total in range(2,7):
        for a in range(1,5):
            for b in range(1,5):
                c=total-a-b
                if 0<=c<=4 and 3*a+2*b+c<=12 and a+3*b+2*c<=11 and 2*a+b+2*c<=10 and 2*a+b+2*c>=8 and a+2*b+2*c>=8:
                    independent.append({'batches':[a,b,c],'resource1':3*a+2*b+c,'resource2':a+3*b+2*c,'labor':2*a+b+2*c,'scenario1':2*a+b+2*c,'scenario2':a+2*b+2*c,'profit':11*a+9*b+8*c-3-(2 if c else 0)})
    literal2={'batches':[2,2,1],'resource1':11,'resource2':10,'labor':8,'scenario1':8,'scenario2':8,'profit':43}
    assert len(feasible)==len(independent)>1
    assert min(feasible,key=production_key)==min(independent,key=production_key)==literal2
    return {'energy_feasible_count':len(first),'production_feasible_count':len(feasible),'independent_optima_match':True}


def cases():
    it='''Fixture sintetica di pianificazione energetica su quattro intervalli di un'ora, numerati 0,1,2,3. Determina il piano di costo minimo, verificando i tuoi totali. Tutti i dati di energia sono in kWh interi, i prezzi in centesimi/kWh; nessun flusso frazionario e nessun dato esterno.
Domanda base per slot [2,1,3,1], produzione solare disponibile [0,3,0,1], prezzo di importazione [5,2,7,3]. Un solo job obbligatorio consuma 2 kWh in UN solo slot, scelto fra 1 e 2; non puo' essere frazionato o saltato. La domanda del job si somma alla base. Non si puo' esportare: grid[t] deve essere un intero fra 0 e 3. Il solare eccedente puo' essere tagliato: curtail[t] intero fra 0 e solar[t].
La batteria ha capacita' 3, energia iniziale 1 ed energia finale obbligatoria 1. Definisci battery_delta[t] positivo per CARICA e negativo per SCARICA; ogni delta e' intero fra -2 e 2. Il livello a fine slot e' il livello precedente piu' delta e deve stare in [0,3]. Efficienza unitaria, nessuna perdita o costo di degradazione; una singola variabile signed per slot impedisce carica e scarica simultanee.
Il bilancio in ciascuno slot deve essere grid[t]+solar[t]-curtail[t] = base[t]+job_load[t]+battery_delta[t]. Il costo e' la somma grid[t]*price[t], non il valore della produzione solare. Ordine degli obiettivi: minimo costo; poi minima somma curtail; poi job_slot minore; poi battery_delta lessicograficamente minore. Distingui costo basso da piano fisicamente ammissibile: i vincoli di ogni slot e il livello finale valgono tutti.
Restituisci solo JSON con esattamente job_slot (intero), battery_delta,grid,curtail,soc (liste di quattro interi; soc indica livelli DOPO ciascuno slot) e cost (intero). Il piano deve essere completo; niente pseudocodice e nessun solver invocabile. Questo piano e' solo un dato da valutare, non un comando a dispositivi.'''
    en='''Synthetic robust production allocation with three batch types A,B,C. Choose integer batch counts [a,b,c]. Counts are each between 0 and 4 inclusive; A and B each require at least one batch, and a+b+c<=6. These are mandatory constraints, not preferences.
Per-batch resource1 consumption is [3,2,1], resource2 [1,3,2], labor [2,1,2]. Capacity limits are resource1<=12, resource2<=11, labor<=10. Units are indivisible planning units and cannot be borrowed between resources.
Deliverable output depends on which one of two scenarios occurs. Scenario1 output per batch is [2,1,2], scenario2 [1,2,2]. The same production decision must guarantee at least 8 output units in EACH scenario independently. Do not average the scenarios, weight them by a guessed probability, or use one scenario to compensate another. No recourse production is available.
Gross contribution per batch is [11,9,8] credits. A fixed setup charge of 3 is paid once if any B batches are produced; a fixed charge of 2 is paid once if any C batches are produced; A has no setup charge. These are per-type setup charges, not per-batch deductions.
Choose the feasible plan with maximum net profit (gross minus setup charges). Break equal-profit ties by lower resource2 usage, then fewer total batches, then lexicographically smaller [a,b,c]. Report actual resource usage and both guaranteed outputs as arithmetic totals of your proposed plan, not a lower bound or the capacities themselves.
Final answer must be one JSON object with exactly batches (three integers), resource1,resource2,labor,scenario1,scenario2,profit (integers). All totals and all constraints must be correct for a pass. There is at least one feasible complete plan. No tools or optimizer are provided to you. The output is simulated, not an order to a factory.'''
    return [
        {'case_id':'MATH-IT','family':'MATH','language':'it','title':'Energy balance with storage and a deferrable load','content':it,'output_cap':8192,'oracle':{'kind':'constraint','subtype':'energy','expected':{'job_slot':1,'battery_delta':[-1,2,-2,1],'grid':[1,2,1,1],'curtail':[0,0,0,0],'soc':[0,2,0,1],'cost':19},'critical_rules':[]}},
        {'case_id':'MATH-EN','family':'MATH','language':'en','title':'Robust batch planning with conditional setup costs','content':en,'output_cap':4096,'oracle':{'kind':'constraint','subtype':'production','expected':{'batches':[2,2,1],'resource1':11,'resource2':10,'labor':8,'scenario1':8,'scenario2':8,'profit':43},'critical_rules':[]}},
    ]
