"""Guards the user-data map that retention, deletion, and attribution rely on.

The point of these tests is drift. The registry is only trustworthy if adding a
table to the schema without classifying it *fails* — otherwise an unmapped
pocket of user data appears silently, and the first time anyone notices is
during an incident or an erasure request.
"""
import pytest

from services.user_data_registry import (
    EXCLUDED_TABLES,
    USER_TABLES,
    audit_coverage,
)


def test_every_table_is_classified():
    unaccounted = audit_coverage()
    assert not unaccounted, (
        "These tables are in the schema but not in services/user_data_registry.py: "
        f"{unaccounted}. Add each to USER_TABLES (with its user column, and a "
        "retention period if the rows should age out) or to EXCLUDED_TABLES with "
        "a reason. Leaving one unclassified silently breaks retention, deletion, "
        "and tenant attribution."
    )


def test_each_table_has_exactly_one_ownership_mechanism():
    for spec in USER_TABLES:
        assert bool(spec.user_column) != bool(spec.via), (
            f"{spec.table}: set exactly one of user_column (direct) or via (indirect)"
        )


def test_no_duplicate_registrations():
    names = [t.table for t in USER_TABLES]
    assert len(names) == len(set(names)), "a table is registered twice"
    assert not (set(names) & set(EXCLUDED_TABLES)), "a table is both registered and excluded"


def test_retention_needs_a_timestamp_to_measure_from():
    for spec in USER_TABLES:
        if spec.retention_days:
            assert spec.timestamp_column, (
                f"{spec.table}: retention_days is set but no timestamp_column, so "
                "nothing can be aged out"
            )


def test_indirect_ownership_resolves_through_a_registered_parent():
    registered = {t.table for t in USER_TABLES}
    for spec in USER_TABLES:
        if spec.via:
            _, parent, _ = spec.via
            assert parent in registered, (
                f"{spec.table} is owned via {parent}, which is not itself registered — "
                "deleting the parent first would orphan these rows"
            )


@pytest.mark.parametrize("spec", USER_TABLES, ids=lambda s: s.table)
def test_where_clause_is_parameterized(spec):
    clause = spec.where_clause()
    assert ":uid" in clause, f"{spec.table}: where clause must bind :uid, never interpolate"
