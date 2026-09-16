# Dataset Provenance

This document is a mandatory artifact for the Future Health Connectathon. It details the provenance, licensing, and limitations of every dataset used to validate the Qalb قلب ECG signal processing pipeline.

**No synthetic or AI-generated ECG data is used anywhere in this system.**

---

## 1. PTB-XL (Primary Validation Dataset)

- **Source**: PhysioNet
- **Reference**: Wagner, P., Strodthoff, N., Bousseljot, R., Kreiseler, D., Lunze, F.I., Samek, W., Schaeffter, T. (2020). *PTB-XL, a large publicly available electrocardiography dataset*. Scientific Data.
- **DOI**: [10.13026/cmsy-5161](https://doi.org/10.13026/cmsy-5161)
- **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **Dataset Specs**: 21,837 clinical 12-lead ECG records from 18,885 patients. Duration: 10 seconds. Sampling frequency: 500 Hz.
- **De-identification**: The original study pseudonymized the records per ethics approval. No PII is included in the downloaded waveforms.
- **Known Limitations**: Strong European population bias. Minimal paediatric representation.
- **Usage in Qalb**: Used for `loader.py` unit tests, pipeline regression tests, and demo record generation.

---

## 2. QT Database (QTc Benchmark)

- **Source**: PhysioNet
- **Reference**: Laguna, P., Mark, R. G., Goldberger, A. L., Moody, G. B. (1997). *A database for evaluation of algorithms for measurement of QT and other waveform intervals in the ECG*. Computers in Cardiology.
- **DOI**: [10.13026/C24K53](https://doi.org/10.13026/C24K53)
- **License**: Open Data Commons Attribution License v1.0 (ODC-BY 1.0)
- **Dataset Specs**: 105 fifteen-minute two-lead ECGs with manual expert annotations of P, QRS, and T wave boundaries.
- **Known Limitations**: Very small N. Manual annotations carry subjective inter-rater variability.
- **Usage in Qalb**: Used exclusively for interval accuracy validation (establishing the QTc ±15ms benchmark).

---

## 3. LUDB - Lobachevsky University Electrocardiography Database (Fallback Validation)

- **Source**: PhysioNet
- **Reference**: Kalyakulina, A. I., Yusipov, I. I., Moskalenko, V. A., Nikolskiy, A. V., Kozlov, A. A., Kosonogov, K. A., Zolotykh, N. Y., Ivanchenko, M. V. (2020). *LUDB: a new open-access validation tool for electrocardiogram delineation algorithms*. Frontiers in Physiology.
- **DOI**: [10.13026/qwde-4j96](https://doi.org/10.13026/qwde-4j96)
- **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **Dataset Specs**: 200 12-lead ECG records (10 seconds each) with comprehensive manual delineations of all complexes.
- **Usage in Qalb**: Used to validate the NeuroKit2 delineation fallback strategy.
