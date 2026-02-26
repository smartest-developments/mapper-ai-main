# Intended Match Hints (Synthetic)

The following pairs are intentionally designed to be likely matches with sparse overlap:

1. Record `2` <-> Record `11`
- Shared signal: same `Electronic Address` -> same `EMAIL_ADDRESS` feature (`shared.persona.01@example.invalid`)
- Sparse pattern: record 11 has many nulls.

2. Record `5` <-> Record `18`
- Shared signal: same `idDocumentNumber` -> same `OTHER_ID` (`DOC_MATCH_02`)
- Sparse pattern: record 18 only keeps minimal identity data.

3. Record `8` <-> Record `20`
- Shared signal: same `LEI` -> same `LEI_NUMBER` (`LEI_MATCH_03`)
- Sparse pattern: record 20 has mostly nulls except LEI.

4. Record `10` <-> Record `16`
- Shared signals: same `Tax ID` and `CRN` (`TAX_MATCH_04`, `CRN_MATCH_04`)
- Sparse pattern: record 16 intentionally partial.
