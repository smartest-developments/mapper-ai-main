# Stakeholder Summary - output.jsonl

## Executive Summary

| Metric | Value |
|---|---|
| Records processed | 10 |
| Data sources in output | PARTNERS (10) |
| Records with Partner ID for matching | 10 (100.0%) |
| Records with Business Relation ID for matching | 10 (100.0%) |
| Records missing RECORD_ID | 0 (0.0%) |

## Entity Mix

| Record Type | Count | Percent |
|---|---|---|
| ORGANIZATION | 4 | 40.0% |
| PERSON | 6 | 60.0% |

## Matching Signal Coverage

| Signal | Coverage |
|---|---|
| Name | 10/10 (100.0%) |
| Address | 10/10 (100.0%) |
| Tax ID | 10/10 (100.0%) |
| Partner ID | 10/10 (100.0%) |
| Business Relation ID | 10/10 (100.0%) |

## Data Quality Snapshot

| Check | Result |
|---|---|
| Other ID includes country | 10/10 records complete |
| Address mapped as ADDR_FULL | 10/10 records |
| Address mapped with ADDR_LINE1 | 0/10 records |

## Analyzer Findings (Simplified)

Critical issues:
- DATA_SOURCE not found: PARTNERS (records: 10)

Warnings: none found.

## Business Interpretation

The dataset is consistently mapped with person/organization typing and includes both Partner ID and Business Relation ID as matching signals.
Before loading into Senzing, ensure the DATA_SOURCE value is registered in Senzing configuration.
