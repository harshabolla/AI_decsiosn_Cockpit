"""
SQL Validation — Security and Business Rules
============================================
Validates generated SQL before execution:
  - Blocks DML/DDL statements
  - Detects dangerous patterns
  - Extracts referenced tables/columns
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DDL, DML

_FORBIDDEN_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "CREATE", "REPLACE", "MERGE", "EXEC",
    "EXECUTE", "CALL", "COPY", "PUT", "GET",
}


@dataclass
class SQLValidationResult:
    valid: bool
    status: str  # "valid" | "invalid" | "warning"
    errors: list[str]
    warnings: list[str]
    tables: list[str]
    is_read_only: bool = True  # False if any forbidden write/DDL keyword detected


def validate_sql(sql: str) -> SQLValidationResult:
    """
    Validates SQL for security and policy compliance.
    Returns structured validation result.
    """
    errors: list[str] = []
    warnings: list[str] = []
    tables: list[str] = []

    is_read_only: bool = True

    if not sql or not sql.strip():
        return SQLValidationResult(valid=False, status="invalid", errors=["Empty SQL"], warnings=[], tables=[], is_read_only=False)

    # Parse
    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return SQLValidationResult(valid=False, status="invalid", errors=["Could not parse SQL"], warnings=[], tables=[], is_read_only=False)

    stmt: Statement = parsed[0]

    # Check statement type
    stmt_type = stmt.get_type()
    if stmt_type and stmt_type.upper() != "SELECT":
        errors.append(f"Only SELECT statements are allowed. Got: {stmt_type}")
        is_read_only = False

    # Token-level keyword check
    for token in stmt.flatten():
        if token.ttype in (DDL, DML, Keyword):
            kw_val = token.value.upper()
            if kw_val in _FORBIDDEN_KEYWORDS:
                errors.append(f"Forbidden SQL keyword: {kw_val}")
                is_read_only = False

    # Extract table names (simple regex approach)
    table_pattern = re.compile(
        r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        re.IGNORECASE,
    )
    tables = list(set(table_pattern.findall(sql)))

    # Check for known allowed tables
    allowed_tables = {"fact_sales", "fact_inventory", "dim_product", "dim_region", "dim_date"}
    unknown_tables = [t for t in tables if t.lower() not in allowed_tables]
    if unknown_tables:
        warnings.append(f"Unknown tables referenced: {unknown_tables}")

    # Check for potential SQL injection patterns in the SQL itself
    if re.search(r"--\s*\w", sql) or "/*" in sql:
        warnings.append("SQL contains comments — review for injection risk.")

    valid = len(errors) == 0
    status = "valid" if valid and not warnings else ("warning" if valid else "invalid")

    return SQLValidationResult(
        valid=valid,
        status=status,
        errors=errors,
        warnings=warnings,
        tables=tables,
        is_read_only=is_read_only,
    )
