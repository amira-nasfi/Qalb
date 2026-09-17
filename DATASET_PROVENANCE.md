# Dataset Provenance

This document details the provenance, licensing, and limitations of all datasets used in the Qalb (قلب) ECG signal processing and clinical interpretation platform.

**No synthetic or AI-generated ECG signal is used as clinical evidence anywhere in this system.**

---

## 1. LUDB — Lobachevsky University Electrocardiography Database

- **DOI**: [10.13026/qwde-4j96](https://doi.org/10.13026/qwde-4j96)
- **Source**: PhysioNet
- **Reference**: Kalyakulina, A. I., Yusipov, I. I., Moskalenko, V. A., Nikolskiy, A. V., Kozlov, A. A., Kosonogov, K. A., Zolotykh, N. Y., Ivanchenko, M. V. (2020). *LUDB: a new open-access validation tool for electrocardiogram delineation algorithms*. Frontiers in Physiology, 11, 588.
- **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **Specifications**: 200 twelve-lead ECG records, 10 seconds duration each, sampled at 500 Hz.
- **Annotations**: Per-lead cardiologist annotations of P, QRS, and T boundaries (onsets and offsets) across 12 leads.
- **Usage in Qalb**: Used for delineation calibration (empirical boundary offsets) and for all reported validation figures (beat detection sensitivity, interval medians, rhythm classification, and boundary accuracy).
- **Known Limitations**: LUDB is amplitude-normalised per lead to a 1.000 mV span, so absolute-voltage criteria (ST segment deviations, ventricular hypertrophy, microvoltage, electrical axis) are not computable on it.

---

## Unused Datasets

PTB-XL and the QT Database were **never downloaded** to this project. All validation benchmarks and delineation calibrations are performed strictly against real clinical records from LUDB.
