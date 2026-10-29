# Incident du 29/10/2026 — erreur UTF-8 en queue de journal d'audit

Campagne lancée sur la machine de soutenance (DESKTOP-7S6DMNB), dossier
`/mnt/c/Users/dell/Desktop/art/projet`, run `TI-20261029-124519-5609`.
Scénarios N01–A15 verts, arrêt sur A16 :

```
File "src/ti_server/audit.py", line 61, in _last
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa9 in position 0
Code de sortie : 1
```

Transcription : `console_tests_20261029_134518.txt`.

## Cause

`AuditLog._last` relisait les 8 192 derniers octets du journal en mode texte sans
s'aligner sur une fin de ligne. Quand `taille - 8192` tombe entre les deux octets
d'un « é » (0xC3 0xA9), la lecture commence sur 0xA9 et le décodage échoue.
Défaut latent dépendant de la taille exacte du fichier.

## Reproduction

`tests/test_audit_tail_utf8.py` construit un journal dont la frontière coupe un « é ».
Avant correctif : `UnicodeDecodeError 'utf-8' codec can't decode byte 0xa9 in position 0`.
Après correctif : `append` réussit, `seq=2`, `prev_hash` repris correctement.

## Correctif

`_last` lit désormais en binaire, écarte la ligne partielle en tête de fenêtre,
décode la dernière ligne complète ; `append` écrit les octets UTF-8 explicitement.
Fichier : `src/ti_server/audit.py`, SHA-256 `74ff9e9f…1821cf` (identique workspace et Bureau).

## Vérification après correctif

- Régression : `[OK ] queue de journal alignée`.
- Workspace (ext4) : 31/31, audit 116/115, p95 6,48 ms.
- Bureau (DrvFs) : 31/31, audit 116/115, p95 50,57 ms, sortie 0 — run `TI-20261029-125411-ebc2`,
  transcription `console_tests_20261029_135410.txt`.
- Le rapport cite la campagne du 27/10 (`TI-20261027-131611-293b`, p95 12,42 ms) : inchangée,
  ces exécutions sont archivées séparément.
