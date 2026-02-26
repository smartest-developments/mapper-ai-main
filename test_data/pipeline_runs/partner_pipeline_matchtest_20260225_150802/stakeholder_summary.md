# Stakeholder Summary - output.jsonl

## Executive Summary

| Metric | Value |
|---|---|
| Records processed | 20 |
| Data sources in output | PARTNERS (20) |
| Records with Partner ID for matching | 0 (0.0%) |
| Records with Business Relation ID for matching | 0 (0.0%) |
| Records missing RECORD_ID | 0 (0.0%) |

## Entity Mix

| Record Type | Count | Percent |
|---|---|---|
| ORGANIZATION | 8 | 40.0% |
| PERSON | 12 | 60.0% |

## Matching Signal Coverage

| Signal | Coverage |
|---|---|
| Name | 20/20 (100.0%) |
| Address | 20/20 (100.0%) |
| Tax ID | 17/20 (85.0%) |
| Partner ID | 0/20 (0.0%) |
| Business Relation ID | 0/20 (0.0%) |

## Data Quality Snapshot

| Check | Result |
|---|---|
| Other ID includes country | 20/20 records complete |
| Address mapped as ADDR_FULL | 0/20 records |
| Address mapped with ADDR_LINE1 | 16/20 records |

## Analyzer Findings (Simplified)

Critical issues:
- DATA_SOURCE not found: PARTNERS (records: 20)

Warnings:
- LEI_NUMBER < 25% populated (records: )
- LEI_NUMBER < 80% unique (records: )
- WEBSITE < 25% populated (records: )

## Business Interpretation

The dataset is consistently mapped with person/organization typing and includes both Partner ID and Business Relation ID as matching signals.
Before loading into Senzing, ensure the DATA_SOURCE value is registered in Senzing configuration.
