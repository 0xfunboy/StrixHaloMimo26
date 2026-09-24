"""Self-contained technical problems with analytic and independent arithmetic checks."""
from __future__ import annotations
import math
from fractions import Fraction


def cases():
    it='''Esperimento termico SINTETICO con dati ideali, non un consiglio su un impianto reale. Un corpo a temperatura uniforme T scambia calore con un ambiente costante Ta=20 gradiC. Il modello valido nell intero intervallo e' C*dT/dt=P-k*(T-Ta), con C in J/K, k in W/K, P in W e tempo in secondi. C e k sono costanti positivi ma ignoti. Non ci sono cambi di fase, ritardi di misura o altri flussi. Le derivate misurate sotto sono istantanee esatte.
Esperimento di identificazione: con P=120W, quando T=30C si misura dT/dt=0.16K/s; quando T=50C si misura dT/dt=0.08K/s. Usa entrambe le misure, non una capacita' ricavata ignorando le perdite. Per il modello a potenza costante, se x=T-Ta, x(t)=P/k+(x(0)-P/k)*exp(-k*t/C).
Secondo esperimento, stesso corpo e ambiente, con P=60W costanti e Tiniziale=25C. Calcola: temperatura di equilibrio; tempo positivo necessario per raggiungere T=40C; energia elettrica immessa fino a quel momento; incremento di energia interna; energia ceduta all ambiente fino a quel momento. Conservazione dell energia: energia immessa = incremento interno + energia ceduta. Specifica inoltre se T=47C e' raggiungibile in un tempo finito con P60 e quello stato iniziale. Se non lo e', il tempo deve essere null, non negativo o infinito serializzato.
Valuta anche la proposta di usare la derivata INIZIALE del secondo esperimento come pendenza costante per stimare il tempo verso40C: calcola quella stima lineare e il suo errore percentuale firmato rispetto al tempo esatto, (lineare-esatto)/esatto*100. Non arrotondare i coefficienti durante i passaggi. Le temperature inC e differenze inK sono coerenti nel modello; non moltiplicare l energia per273.15.
Risposta finale soltanto JSON con esattamente C_J_per_K,k_W_per_K,equilibrium_C,time_to_40_s,input_energy_J,stored_energy_J,lost_energy_J (numeri), reaches_47 (booleano),time_to_47_s (numero oppure null),initial_slope_K_per_s,linear_time_to_40_s,linear_error_percent (numeri), governing_assumptions (lista di stringhe). governing_assumptions deve contenere esattamente, in qualunque ordine, constant_environment,lumped_temperature,constant_C_and_k,constant_power. Precisione: errore assoluto<=0.01 sui numeri. Nessuna misura aggiuntiva o azione reale richiesta.'''
    exact_time=250*math.log(4)
    expected_it={
        'C_J_per_K':600.0,'k_W_per_K':2.4,'equilibrium_C':45.0,'time_to_40_s':exact_time,
        'input_energy_J':60*exact_time,'stored_energy_J':9000.0,'lost_energy_J':60*exact_time-9000,
        'reaches_47':False,'time_to_47_s':None,'initial_slope_K_per_s':0.08,
        'linear_time_to_40_s':187.5,'linear_error_percent':(187.5-exact_time)/exact_time*100,
        'governing_assumptions':['constant_environment','lumped_temperature','constant_C_and_k','constant_power'],
    }
    en='''Synthetic diagnostic decision problem. Do not infer medical or safety advice. A population of industrial cartridges has a latent fault with prior probability0.02. A and B are binary test outputs. Because the tests share a sensor, they are NOT conditionally independent. Use the JOINT probabilities in this table; do not multiply marginal test rates.
For faulty cartridges: P(A+,B+)=0.81; P(A+,B-)=0.09; P(A-,B+)=0.04; P(A-,B-)=0.06.
For healthy cartridges: P(A+,B+)=0.03; P(A+,B-)=0.07; P(A-,B+)=0.12; P(A-,B-)=0.78.
These probabilities are exact inputs for the task; no empirical sample counts or uncertainty model were supplied. Bayes rule uses the unconditional population prior above.
For each outcome ++ and +- calculate posterior probability of fault. A perfect inspection costs20credits, detects every fault and removes all downstream fault loss at no additional cost. Not inspecting costs1000credits if the cartridge is faulty and0 if healthy. Select INSPECT or SKIP for each outcome by minimum expected cost conditional on the observed outcome; ties would choose SKIP. Report the expected cost saved by the selected action compared with always skipping, separately for these outcomes.
Now consider 10000 cartridges sampled from the population (use expected counts, not integers forced by rounding). Compute the expected number with outcome++, faulty among++, healthy among++, and faulty missed by a rule that INSPECTS ONLY ++. This latter rule must not inspect +- even if your earlier optimal decision would do so; these are two distinct policies. Report the total expected cost of that ++-only rule, including every inspection and losses for all uninspected faults.
Also compute the expected total cost of a policy that inspects BOTH ++ and +-, and the difference (both-policy cost minus ++-only cost). Explain the information limit by reporting sample_based_95pct_CI_available as a boolean and sampling_uncertainty_interval as null unless the supplied information determines a sample-based confidence interval. Do not invent a sample size used to estimate the table:10000 is the application population, not a validation sample.
Final response: one JSON object with exactly posterior_pp,posterior_pn,decision_pp,decision_pn,saving_pp,saving_pn,expected_pp,expected_faulty_pp,expected_healthy_pp,missed_faults_pp_only,total_cost_pp_only,total_cost_pp_or_pn,cost_difference,sample_based_95pct_CI_available,sampling_uncertainty_interval. Probability tolerance1e-8; count and cost tolerance0.01. Numeric values must be finite; decision values are INSPECT or SKIP. No commands to equipment.'''
    expected_en={
        'posterior_pp':float(Fraction(27,76)),'posterior_pn':float(Fraction(9,352)),
        'decision_pp':'INSPECT','decision_pn':'INSPECT','saving_pp':1000*float(Fraction(27,76))-20,
        'saving_pn':1000*float(Fraction(9,352))-20,
        'expected_pp':456.0,'expected_faulty_pp':162.0,'expected_healthy_pp':294.0,
        'missed_faults_pp_only':38.0,'total_cost_pp_only':47120.0,
        'total_cost_pp_or_pn':43200.0,'cost_difference':-3920.0,
        'sample_based_95pct_CI_available':False,'sampling_uncertainty_interval':None,
    }
    return [
        {'case_id':'SCI-IT','family':'SCIENCE','language':'it','title':'Thermal identification and energy conservation','content':it,'output_cap':8192,
         'oracle':{'kind':'numeric','expected':expected_it,'default_tolerance':0.01,'unordered_paths':['$.governing_assumptions'],'nullable_paths':{'$.time_to_47_s':'number'},'critical_rules':[]}},
        {'case_id':'SCI-EN','family':'SCIENCE','language':'en','title':'Dependent diagnostic tests and two distinct decision policies','content':en,'output_cap':4096,
         'oracle':{'kind':'numeric','expected':expected_en,'default_tolerance':0.01,'tolerances':{'$.posterior_pp':1e-8,'$.posterior_pn':1e-8},'nullable_paths':{'$.sampling_uncertainty_interval':'array'},'critical_rules':[]}},
    ]


def check_independent():
    a,b=cases();e=a['oracle']['expected']
    assert abs(120-e['k_W_per_K']*10-e['C_J_per_K']*.16)<1e-10
    assert abs(120-e['k_W_per_K']*30-e['C_J_per_K']*.08)<1e-10
    tau=e['C_J_per_K']/e['k_W_per_K'];te=e['time_to_40_s']
    assert abs(20+25+(5-25)*math.exp(-te/tau)-40)<1e-10
    # Integrate loss analytically through x(t), independently of input-minus-storage.
    integrated_loss=2.4*(25*te-20*tau*(1-math.exp(-te/tau)))
    assert abs(integrated_loss-e['lost_energy_J'])<1e-8
    assert e['reaches_47'] is False and e['equilibrium_C']<47
    pop=10000;fault=Fraction(1,50);healthy=1-fault
    fp=pop*fault*Fraction(81,100);hp=pop*healthy*Fraction(3,100)
    fn=pop*fault*Fraction(9,100);hn=pop*healthy*Fraction(7,100)
    ex=b['oracle']['expected']
    assert fp==162 and hp==294 and fp/(fp+hp)==Fraction(27,76)
    assert fn==18 and hn==686 and fn/(fn+hn)==Fraction(9,352)
    only=20*(fp+hp)+1000*(pop*fault-fp)
    both=20*(fp+hp+fn+hn)+1000*(pop*fault-fp-fn)
    assert float(only)==ex['total_cost_pp_only'] and float(both)==ex['total_cost_pp_or_pn']
    assert float(both-only)==ex['cost_difference']
    return {'thermal_equations_and_integrated_loss':'PASS','joint_probability_fraction_arithmetic':'PASS'}
