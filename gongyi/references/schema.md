# AI Project Knowledge Base — Schema Reference

## Overview

8 core tables + 2 optional tables. All tables use SQLite.

## Core Tables

### meta — Project Metadata

```sql
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

| key | Description | Example |
|-----|-------------|---------|
| name | Project name | my-project |
| version | Current version | v0.4.0 |
| language | Primary language | Go |
| framework | Main framework | gin / gin-like mux |
| database | Backend database | MySQL |
| port | Service port | 5232 |
| description | One-line description | API token management and proxy service |
| entry_point | Main entry file | main.go |
| total_lines | Total source lines | 5361 |
| total_functions | Total functions | 119 |
| total_tables | Database tables | 7 |
| generated_at | Build timestamp | 2026-05-21T11:00:00Z |

---

### modules — Module Skeleton

```sql
CREATE TABLE modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- Module name: proxy, billing, auth
    layer TEXT,                   -- api/handler/service/repository/model/middleware/proxy/billing/user/admin/sync
    responsibility TEXT,          -- One-line responsibility
    entry_func TEXT,              -- Main entry function name
    file_path TEXT,               -- Source file path
    line_start INTEGER,           -- Start line number
    line_end INTEGER,             -- End line number
    deps TEXT,                    -- Dependent modules (JSON array)
    sideeffects TEXT,             -- Side effects (global vars, singletons)
    constraints TEXT,             -- Hard constraints for this module
    notes TEXT
);
```

---

### symbols — Symbol Table (Functions/Structs/Types)

```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER,            -- FK to modules.id
    name TEXT NOT NULL,           -- Function/struct/type name
    signature TEXT,               -- Full signature
    role TEXT,                    -- function/struct/interface/type/constant/variable
    receiver TEXT,                -- Go receiver type (e.g. *TokenFactory)
    params TEXT,                  -- Parameters description
    returns TEXT,                 -- Return values description
    calls TEXT,                   -- Functions this symbol calls (JSON array)
    called_by TEXT,               -- Functions that call this symbol (JSON array)
    line_number INTEGER,          -- Definition line number
    notes TEXT
);
```

---

### api_routes — API Routes

```sql
CREATE TABLE api_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method TEXT,                  -- GET/POST/PUT/DELETE/PATCH/OPTIONS/HEAD/*
    path TEXT NOT NULL,           -- URL path pattern
    handler TEXT NOT NULL,        -- Handler function name
    auth TEXT,                    -- none/bearer/apikey/session/admin
    group_name TEXT,              -- Route group (user/admin/proxy/public)
    description TEXT,
    file_path TEXT,               -- Where defined
    line_number INTEGER,
    notes TEXT
);
```

---

### tables — Database Tables

```sql
CREATE TABLE tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- Table name
    prefix TEXT,                  -- Table prefix (e.g. tf_)
    purpose TEXT,                 -- What this table stores
    fields TEXT,                  -- Field definitions (JSON array)
    relations TEXT,               -- Relationships (JSON array)
    primary_key TEXT,             -- Primary key field(s)
    foreign_keys TEXT,            -- Foreign key definitions (JSON)
    indexes TEXT,                 -- Index definitions (JSON)
    notes TEXT
);
```

**fields JSON format:**
```json
[
  {"name": "id", "type": "int", "pk": true, "comment": "Primary key"},
  {"name": "email", "type": "varchar(191)", "unique": true, "comment": "User email"},
  {"name": "balance", "type": "decimal(10,4)", "comment": "Balance in yuan"}
]
```

---

### decisions — Architecture Decision Records (ADR)

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,    -- ADR-001 format
    title TEXT NOT NULL,
    context TEXT,                 -- Background/problem statement
    decision TEXT NOT NULL,       -- What was decided
    consequences TEXT,            -- Trade-offs and consequences
    risks TEXT,                   -- Known risks
    mitigations TEXT,             -- Mitigation measures
    status TEXT,                  -- accepted/proposed/superseded/rejected
    source_file TEXT,             -- Where this decision was found in code
    notes TEXT
);
```

---

### constraints — Business & Technical Constraints

```sql
CREATE TABLE constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,                -- transactional/integrity/business/security/schema/api
    rule TEXT NOT NULL,           -- The constraint description
    severity TEXT,                -- critical/warning/info/forbidden
    affected_modules TEXT,        -- Affected module names (JSON array)
    affected_tables TEXT,         -- Affected table names (JSON array)
    enforcement TEXT,             -- How this is enforced (code/DB/test)
    source_location TEXT,         -- Where in code this is enforced
    notes TEXT
);
```

**category values:**
- `transactional` — ACID/lock/rollback requirements
- `integrity` — Data consistency rules
- `business` — Business logic rules
- `security` — Security requirements
- `schema` — Database schema constraints
- `api` — API contract rules

**severity values:**
- `forbidden` — Must NEVER be violated (leads to data corruption or security breach)
- `critical` — Must be followed (leads to incorrect behavior)
- `warning` — Should be followed (may cause edge case issues)
- `info` — For reference

---

### config — Configuration Items

```sql
CREATE TABLE config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT,                   -- global/database/session/billing/security/email
    key TEXT NOT NULL,
    value TEXT,                   -- Default value or location
    type TEXT,                    -- string/int/bool/secret
    description TEXT,
    source TEXT,                  -- Where configured (.env / config struct / hardcoded)
    notes TEXT
);
```

---

## Optional Tables

### data_flow — Data Flow Documentation

```sql
CREATE TABLE data_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- Flow name (e.g. "User Request → Proxy → Billing")
    description TEXT,             -- What this flow does
    steps TEXT,                   -- Step-by-step flow (JSON array)
    involved_modules TEXT,        -- Module names (JSON array)
    involved_tables TEXT,         -- Table names (JSON array)
    notes TEXT
);
```

### change_log — Code Change Log

```sql
CREATE TABLE change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,               -- When change was recorded
    module TEXT,                  -- Affected module
    symbol TEXT,                  -- Affected function/struct
    change_type TEXT,             -- added/modified/deleted
    description TEXT,             -- What changed
    author TEXT,                  -- Who made the change (AI session ID or human)
    notes TEXT
);
```

---

## Common Queries

### Get module by name
```sql
SELECT * FROM modules WHERE name = ?;
```

### Get all critical constraints
```sql
SELECT rule, severity, affected_modules FROM constraints WHERE severity IN ('critical', 'forbidden');
```

### Get function signature
```sql
SELECT signature, params, returns FROM symbols WHERE name = ? AND role = 'function';
```

### Get all API routes in a group
```sql
SELECT method, path, handler, auth FROM api_routes WHERE group_name = ? ORDER BY path;
```

### Get billing-related constraints
```sql
SELECT c.rule, c.severity
FROM constraints c
WHERE c.affected_modules LIKE '%billing%'
ORDER BY c.severity;
```

### Get module dependencies
```sql
SELECT name, deps FROM modules WHERE deps != '[]' AND deps != '';
```

### Get table schema with fields
```sql
SELECT name, fields, relations FROM tables WHERE name = ?;
```
