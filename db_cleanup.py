"""Remove the rows that hang off a deleted parent row.

The app's foreign keys don't cascade and SQLite doesn't enforce them, so
`db.session.delete(user)` removes only the users row and leaves the student's
progress, answers and reports behind. SQLite also reuses the id of the newest row,
so the next account created can silently inherit that leftover data.

purge_dependents() walks the foreign-key graph and deletes every dependent row,
children before grandchildren, inside the caller's transaction (the caller commits).
"""
from sqlalchemy import inspect, text


def _fk_graph(session):
    """parent table -> [(child table, child column, parent column), ...]"""
    inspector = inspect(session.get_bind())
    graph = {}
    for table in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table):
            parent = fk["referred_table"]
            for child_col, parent_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                graph.setdefault(parent, []).append((table, child_col, parent_col))
    return graph


def _ints(values):
    return sorted({int(v) for v in values if v is not None})


def _purge(session, graph, parent, parent_col, values, counts, seen):
    values = _ints(values)
    if not values:
        return
    in_list = ",".join(str(v) for v in values)          # integers only, so safe to inline
    for child, col, pcol in graph.get(parent, []):
        if pcol != parent_col or (child, col, in_list) in seen:
            continue
        seen.add((child, col, in_list))
        # Grandchildren may reference other columns of this child (normally its id).
        referenced = sorted({g[2] for g in graph.get(child, [])})
        if referenced:
            select_cols = ", ".join(f'"{c}"' for c in referenced)
            rows = session.execute(text(f'SELECT {select_cols} FROM "{child}" WHERE "{col}" IN ({in_list})')).fetchall()
            for i, ref_col in enumerate(referenced):
                _purge(session, graph, child, ref_col, [r[i] for r in rows], counts, seen)
        result = session.execute(text(f'DELETE FROM "{child}" WHERE "{col}" IN ({in_list})'))
        if result.rowcount:
            counts[child] = counts.get(child, 0) + result.rowcount


def purge_dependents(session, table, ids, id_column="id"):
    """Delete every row (at any depth) that references `table`.`id_column` in `ids`.

    Does NOT delete the parent rows themselves. Returns {table_name: rows_deleted}.
    """
    counts = {}
    _purge(session, _fk_graph(session), table, id_column, ids, counts, set())
    return counts
