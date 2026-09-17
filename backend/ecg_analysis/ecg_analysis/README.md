# ecg_analysis

Analyse ECG 12 dérivations : contrôle qualité, segmentation PQRST, mesures,
critères cliniques, compte rendu et priorité de prise en charge.

Bibliothèque pure Python, sans dépendance Django, appelable depuis une vue, une
tâche Celery ou une commande de management.

## Installation

```bash
pip install numpy scipy neurokit2 wfdb pyedflib
```

Déposer le dossier `ecg_analysis/` à la racine du projet Django, à côté de
`manage.py`.

## Appel unique

```python
from ecg_analysis import analyze_to_report

out = analyze_to_report("/media/ecg/2026/09/rec.edf",
                        age=64, sex="M", paced=False,
                        patient_id="P-00421")

out["result"]         # dict complet, sérialisable en JSON, à stocker tel quel
out["report_text"]    # compte rendu texte, prêt pour signature ou PDF
out["report_blocks"]  # structure de blocs pour le rendu React
```

Formats acceptés : `.dat`/`.hea` (WFDB), `.csv`, `.edf`/`.bdf`, ou un tableau
numpy `(n_dérivations, n_échantillons)` en mV avec `fs` fourni.

Le CSV exige une ligne d'en-tête nommant les dérivations. La fréquence
d'échantillonnage est déduite d'une colonne `time` si elle existe, sinon il faut
passer `fs`.

## Structure de `result`

```
ok                  bool
version             version du moteur, à stocker avec le résultat
analysed_at         ISO 8601 UTC
patient             {id, age, sex, paced}
acquisition         {fs_in_hz, duration_s, leads, source}
quality             {acceptable, failed_leads, missing_leads, per_lead, action}
segmentation        {method, calibration_offsets_ms, r_peaks, boundaries,
                     label_lead, labels, label_legend}
measurements        {n_beats, hr_bpm, rr_ms, pnn50, rmssd_ms, n_ectopic,
                     pr_ms, qrs_ms, qt_ms, qtc_bazett_ms, qtc_fridericia_ms}
rhythm              {rhythm, rate, reason, paced}
findings            [{component, finding, severity, measured, threshold,
                      meaning, code}]
triage              {level, priority, label, action, escalate}
limits              liste des limites déclarées
timings             {steps: [{step, duration_ms}], total_ms}
error               présent seulement si ok est false
```

`severity` vaut RED, ORANGE ou GREEN. `triage.priority` vaut 1, 2 ou 3, et 0
quand le tracé est rejeté pour qualité insuffisante.

## Point de décision : qualité

Quand `quality.acceptable` est false, aucune interprétation n'est produite. Le
résultat contient `triage.level = "REJET"` et `escalate = true`. C'est le
signal de réacquisition. Ne pas router un tracé rejeté vers un médecin.

## Point de décision : escalade

`triage.escalate` est vrai dans deux cas : priorité 1 (urgence clinique) et
rejet qualité (réacquisition). Les deux remontent, pour des raisons
différentes, ce que l'audit doit distinguer.

## Segmentation pour le tracé React

`segmentation.labels` est un tableau d'un entier par échantillon :

```
0 fond    1 onde P    2 complexe QRS    3 onde T
```

Il concerne la dérivation nommée dans `segmentation.label_lead`. Pour colorer
les autres dérivations, utiliser `segmentation.boundaries[lead]`, qui donne les
positions en échantillons.

Exemple de rendu, en supposant un tracé déjà dessiné :

```jsx
const COLORS = {1: "#7C6FE8", 2: "#D85A30", 3: "#2E9E8F"};

function Overlay({labels, fs, width, height}) {
  const bands = [];
  let start = 0, cur = labels[0];
  for (let i = 1; i <= labels.length; i++) {
    if (i === labels.length || labels[i] !== cur) {
      if (cur !== 0) bands.push({cls: cur, a: start, b: i});
      start = i; cur = labels[i];
    }
  }
  const px = width / labels.length;
  return (
    <g opacity="0.18">
      {bands.map((b, k) => (
        <rect key={k} x={b.a * px} width={(b.b - b.a) * px}
              y={0} height={height} fill={COLORS[b.cls]} />
      ))}
    </g>
  );
}
```

Le tableau de labels fait un entier par échantillon, soit 5000 valeurs pour
10 s à 500 Hz. Passer `want_labels=False` pour l'omettre si la charge utile
compte, et reconstruire côté client depuis `boundaries`.

## Délais

`timings.steps` donne la durée de chaque étape de l'analyse automatique. C'est
la partie machine de la boucle. Les délais humains (transmission, ouverture,
signature, restitution) se mesurent sur les horodatages du modèle Django, voir
`django_integration.py`.

Ordre de grandeur mesuré : environ 850 ms au total, dont 650 ms de détection
des battements au premier appel (chargement des modules NeuroKit), puis
environ 200 ms sur les appels suivants dans le même processus. Prévoir un
préchauffage au démarrage du worker.

## Intégration Django

`django_integration.py` contient un modèle `EcgStudy` avec machine à états et
horodatages, un modèle `AuditEvent` en append-only, et sept vues DRF couvrant
la boucle : dépôt et analyse, transmission, ouverture, signature, restitution
au SIH, audit, liste de travail.

```bash
python -m ecg_analysis.django_integration models > ecg/models.py
python -m ecg_analysis.django_integration views  > ecg/views.py
python -m ecg_analysis.django_integration urls   > ecg/urls.py
```

À relire et adapter avant migration. La vue de restitution SIH construit un
payload FHIR `DiagnosticReport` mais n'envoie rien : remplacer l'appel commenté.

## Validation mesurée

Sur LUDB, 200 enregistrements 12 dérivations annotés par des cardiologues.

| Composant | Résultat |
|---|---|
| Détection des battements | Se 99,94 %, VPP 99,66 %, erreur médiane 2 ms, 191 enregistrements, 1817 battements |
| Détection sur rythmes appareillés | Se 71,43 % ; le détecteur se verrouille sur le spicule, environ 70 ms avant le QRS |
| Segmentation PQRST | Se 98,4 % début P, 92,9 % fin P, 96,7 % début QRS, 98,1 % fin QRS, 76,7 % fin T |
| Biais de segmentation corrigé | début P +12,8 ms, fin P −18,3 ms, début QRS −6,9 ms, fin QRS −4,4 ms, fin T −19,6 ms |
| Dispersion résiduelle | 2 SD entre 41 et 58 ms, au-dessus des tolérances CSE sur les cinq bornes |
| Intervalles, médianes | FC 64 bpm, PR 159 ms, QRS 94 ms, QT 377 ms, QTcB 402 ms, 176 enregistrements, toutes dans les plages normales publiées |
| Dépistage du rythme irrégulier | Se 100 %, Sp 78,6 %, seuil pNN50 0,35, 200 enregistrements |
| Classification du rythme | 84 % d'accord avec les annotations cardiologues, 200 enregistrements |

## Limites

Pas de critères de voltage : ST, hypertrophie, microvoltage, axe. Ils exigent un
signal calibré en mV, et LUDB est normalisée en amplitude par dérivation, chaque
dérivation étant ramenée à une amplitude crête à crête de 1,000 mV. Constaté
dans les données, confirmé dans les gains par dérivation des en-têtes et dans le
changelog de la version 1.0.1. Sur une base correctement calibrée (PTB-XL, ou un
export d'appareil réel) ces critères sont calculables et les règles restent à
écrire.

Pas de détection des spicules de stimulation. Un spicule dure 0,5 à 2 ms, soit
un seul échantillon à 500 Hz, ce qui ne permet pas de le distinguer d'un front
de QRS raide. La détection exige un échantillonnage à 1 kHz ou plus. Le drapeau
`paced` est donc une entrée fournie par l'appareil, pas une sortie du logiciel.

Pas de bloc AV du 3e degré (exige la dissociation P/QRS), pas de latéralisation
des blocs de branche (exige l'analyse morphologique par dérivation).

Adulte uniquement. Les plages pédiatriques diffèrent.

Aucun modèle entraîné. La segmentation est algorithmique, par transformée en
ondelettes, avec six paramètres calibrés sur données : cinq décalages de bornes
et un seuil pNN50. Un réseau de segmentation entraîné sur LUDB est l'étape
suivante identifiée, et la présente implémentation fournit la baseline chiffrée
contre laquelle le comparer.
