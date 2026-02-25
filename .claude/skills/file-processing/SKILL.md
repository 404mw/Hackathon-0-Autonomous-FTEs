---
name: file-processing
description: >
  Processes dropped files — extracts metadata, categorizes, and routes to the
  appropriate folder. Use when FILE_*.md files appear in Needs_Action/ from the
  filesystem watcher or manual drops.
allowed-tools: Read, Write, Glob, Grep
---

# File Processing

Processes `FILE_*.md` files in `Needs_Action/`, extracts metadata, categorizes them, and routes them for further action.

## When to Invoke

- When a `FILE_*.md` file appears in `Needs_Action/`
- When `vault-triaging` identifies an item with the `FILE_` prefix
- When the user manually drops a file and asks to process it

## Processing Flow

For each `FILE_*.md` file:

1. **Read** the file and its YAML frontmatter
2. **Extract metadata:**
   - Original filename and extension
   - File size (if available in frontmatter)
   - Date detected by watcher
   - Content summary (first 500 characters or structured extraction)
3. **Categorize** by content type:
   - `invoice` — contains invoice-related keywords, amounts, client names
   - `contract` — legal language, terms, signatures
   - `report` — data, charts, analysis
   - `receipt` — transaction records, payment confirmations
   - `correspondence` — letters, memos
   - `document` — general documents that don't fit above categories
   - `unknown` — cannot determine type
4. **Assess priority:**
   - Contains financial data (amounts, account numbers) → `high`
   - Contains deadlines or dates → `normal`
   - General documents → `low`
   - Unknown type → `normal` (flag for human review)
5. **Route** based on category:
   - Financial documents (`invoice`, `receipt`) → create plan for `Accounting/` processing
   - Action-required documents (`contract`, `correspondence`) → create plan via `plan-generating`
   - Informational documents (`report`, `document`) → archive to `Done/`
   - Unknown → flag for human review, do not auto-route
6. **Update frontmatter** with processing results
7. **Log** via `audit-logging`

## Output

Update the `FILE_*.md` frontmatter in place:

```yaml
---
type: file_drop
status: processed
priority: <assessed priority>
created: <original timestamp>
source: filesystem_watcher
original_filename: <original file name>
category: <classified category>
suggested_action: <route or archive>
---
```

## Categorization Keywords

| Category | Keywords |
|----------|----------|
| invoice | invoice, bill, amount due, payment terms, net 30 |
| contract | agreement, terms and conditions, hereby, parties, signature |
| report | analysis, findings, summary, quarterly, metrics |
| receipt | receipt, transaction, paid, confirmation, payment received |
| correspondence | dear, regards, re:, follow-up, attached |

## Rules

1. Never move or delete the original file from `Needs_Action/` — only update frontmatter and create plans.
2. If the file contains sensitive data (financial, personal), set priority to `high` and flag it.
3. Do not attempt to open or process binary files. If the watcher metadata indicates a binary, categorize as `document` and flag for human review.
4. For files categorized as `unknown`, always add a plan step: "Human review required — unable to classify."
5. After processing, invoke `audit-logging` for each file processed.
6. After all files are processed, invoke `dashboard-updating`.
