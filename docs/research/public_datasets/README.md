# Public business and technology datasets for reproducible LEM2 stress testing

This folder contains **attributed, reduced and stratified** subsets of two CC BY 4.0 UCI datasets. They are independently prepared from the public originals; no private-company or user records are included.

## Online Shoppers Purchasing Intention Dataset
- Sakar, C. & Kastro, Y. (2018), UCI ML Repository, DOI: https://doi.org/10.24432/C5F88Q
- Source: https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset
- Public observations: 12,330; this experiment uses 1,600 stratified sampled sessions and six predefined features.
- Revenue target is taken from the original; PageValues is deliberately NOT used.

## AI4I 2020 Predictive Maintenance Dataset
- AI4I 2020 Predictive Maintenance Dataset (2020), UCI ML Repository, DOI: https://doi.org/10.24432/C5HS5C
- Source: https://archive.ics.uci.edu/dataset/601/ai4i
- This is a **synthetic industrial dataset**; 10,000 public points; experiment uses 2,400 stratified sampled points.
- The target is Machine failure; failure-category targets TWF/HDF/PWF/OSF/RNF and device IDs are excluded.

## License and processing
- Both source datasets: Creative Commons Attribution 4.0 International (CC BY 4.0).
- License: https://creativecommons.org/licenses/by/4.0/
- Modifications: fixed class-stratified downsampling (seed 20261112), feature subset, cleaned column names, class column normalized to string.
- Individual 80/20 randomized train/test splits happen later, for experiment seeds 1/7/21/42; only train fits preprocessing and LEM2.
- Source-independent evaluations and metadata: ../teacher_dashboard/data/PUBLIC_COMMERCE_TECH_PILOT_*
- The frozen original 8,820-row matrix is NOT modified; this is a separate 4-seed feasibility pilot.
