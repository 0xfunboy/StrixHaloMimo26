# MiMo Kyojin su NODE02 — uso rapido

## Stato disponibile

```text
NODE02:     02-EVO-X3
Modello:    yamz-labs/MiMo-V2.6-Flash-MOPD-EXL3-Yamz
Revisione:  f895a38f1a3401cf61c8e6f8a9d1decca5198bde
Kyojin:     a3ac00d4a32148229e66c0916fcc3282bf47a3d9
Profilo:    BASE 40960
API NODE02: http://127.0.0.1:18571/v1
Model ID:   mimo-mopd-kyojin
DFlash:     attivo, ndt 7, lossless
```

## Dal NODE01

Il forward manuale è già installato:

```bash
systemctl --user start mimo-kyojin-forward-node02.service
curl --noproxy '*' http://127.0.0.1:18571/health
```

Client del repository MiMo:

```bash
cd /home/funboy/StrixHaloMimo26
python3 scripts/mimo-kyojin-node02-client.py   'Spiega in tre punti il ruolo di un reverse proxy.'
```

Streaming:

```bash
python3 scripts/mimo-kyojin-node02-client.py --stream   'Scrivi una breve funzione TypeScript che normalizza uno slug.'
```

## Dal PC Windows

Aprire un terminale e mantenere questa sessione attiva:

```powershell
ssh -p 7777 -N -o ExitOnForwardFailure=yes `
  -L 127.0.0.1:18571:127.0.0.1:18571 `
  funboy@192.168.1.12
```

In un secondo terminale:

```powershell
curl.exe http://127.0.0.1:18571/health
curl.exe http://127.0.0.1:18571/v1/models
```

Richiesta OpenAI-compatible:

```powershell
$body = @{
  model = 'mimo-mopd-kyojin'
  messages = @(@{ role='user'; content='Rispondi con una frase.' })
  max_completion_tokens = 512
  temperature = 1.0
  top_p = 0.95
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri http://127.0.0.1:18571/v1/chat/completions `
  -Method Post -ContentType 'application/json' -Body $body
```

La porta resta loopback-only su entrambi i nodi. Non esiste un token condiviso con Gufo e HaloClu.

## Gestione sul NODE02

```bash
cd /home/funboy/StrixHaloMimoKyojin
bin/mimo status
bin/mimo logs
bin/mimo stop
bin/mimo start --profile base --mode dflash --wait
```

Il servizio è manuale/statico e non è abilitato al boot.

## Limite LONG

Il profilo 196608 è stato tentato ma il memory guard ha fermato il processo prima di READY, quando la riserva obbligatoria di 8 GiB non era più garantita. Perciò:

```text
BASE 40960: disponibile
LONG 196608: non qualificato / non disponibile
64K code: NOT_RUN
128K document: NOT_RUN
```

Non avviare LONG automaticamente e non descrivere questa installazione come 128K qualificata.
