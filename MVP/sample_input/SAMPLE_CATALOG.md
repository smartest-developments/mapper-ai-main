# Sample Input Catalog

All files contain 500 records in JSON format with top-level metadata and `records` array.

1. `sample_01_legacy_baseline_500.json`
   - Legacy baseline sample kept for continuity with previous MVP runs.
   - Features: original 500-record baseline, mixed PERSON/ORGANIZATION, default sparsity pattern
2. `sample_02_balanced_baseline_500.json`
   - Balanced baseline with default realism and moderate IPG coverage.
   - Features: balanced person/org split, moderate missing fields, standard noise
3. `sample_03_sparse_fields_500.json`
   - High sparsity scenario with many optional fields missing.
   - Features: aggressive null optional fields, harder matching due to low completeness
4. `sample_04_name_noise_500.json`
   - Name formatting noise (case/punctuation/spacing variations).
   - Features: name normalization stress, formatting inconsistencies
5. `sample_05_taxid_noise_500.json`
   - Tax ID quality issues with malformed identifiers on a subset of records.
   - Features: identifier quality degradation, weaker deterministic signals
6. `sample_06_address_noise_500.json`
   - Address inconsistencies and partial address drops.
   - Features: address quality stress, missing residence/street/postal values
7. `sample_07_duplicate_pressure_500.json`
   - Higher duplicate pressure by making subsets look near-identical.
   - Features: larger ambiguous clusters, false positive/negative pressure
8. `sample_08_organization_heavy_500.json`
   - Organization-heavy dataset with more corporate records than persons.
   - Features: organization-heavy, different identifier mix
9. `sample_09_person_heavy_low_ipg_500.json`
   - Person-heavy dataset with low SOURCE IPG labeling coverage.
   - Features: person-heavy, low IPG labels
10. `sample_10_high_ipg_coverage_500.json`
   - High SOURCE IPG coverage for comparison against lower-labeling scenarios.
   - Features: high IPG labels, quality evaluation easier
