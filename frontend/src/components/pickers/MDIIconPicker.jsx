import React, { useEffect, useMemo, useState } from "react";

function normalize(text) {
  return text.trim().toLowerCase();
}

function stripMdiPrefix(text) {
  const t = normalize(text);
  return t.startsWith("mdi:") ? t.slice(4) : t;
}

export default function MdiIconPicker({
  value,
  onChange,
  disabled,
  loadIconIds,
  renderPreview,
  pageSize = 100,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [iconIds, setIconIds] = useState<>(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!isOpen || iconIds !== null || isLoading) return;

    setIsLoading(true);
    loadIconIds()
      .then((ids) => {
        // Defensive: normalize and ensure "mdi:" prefix
        const normalized = ids
          .map((id) => {
            const n = normalize(id);
            return n.startsWith("mdi:") ? n : `mdi:${n}`;
          })
          .filter((id) => id.length > 4);

        setIconIds(normalized);
      })
      .finally(() => setIsLoading(false));
  }, [isOpen, iconIds, isLoading, loadIconIds]);

  // Reset paging when query changes
  useEffect(() => {
    setPage(1);
  }, [query]);

  const filtered = useMemo(() => {
    if (!iconIds) return [];
    const qRaw = normalize(query);
    if (!qRaw) return iconIds;

    const q = stripMdiPrefix(qRaw);
    return iconIds.filter((id) => {
      const idNorm = normalize(id); // "mdi:television"
      const name = stripMdiPrefix(idNorm); // "television"
      return idNorm.includes(qRaw) || name.includes(q);
    });
  }, [iconIds, query]);

  const pageCount = useMemo(() => {
    return Math.max(1, Math.ceil(filtered.length / pageSize));
  }, [filtered.length, pageSize]);

  const currentPage = Math.min(page, pageCount);

  const pageItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, currentPage, pageSize]);

  const canClear = query.trim().length > 0;

  return (
    <div>
      <button type="button" disabled={disabled} onClick={() => setIsOpen(true)}>
        {value ?? "mdi:..."}
      </button>

      {isOpen && (
        <div role="dialog" aria-modal="true">
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search icon (name or mdi:...)"
              autoFocus
            />
            {canClear && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
              >
                Clear
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                // Reset state when closed (as requested)
                setQuery("");
                setPage(1);
              }}
            >
              Close
            </button>
          </div>

          {isLoading && <div>Loading…</div>}

          {!isLoading && iconIds && (
            <>
              <div style={{ marginTop: 8 }}>
                Showing {pageItems.length} of {filtered.length} (page {currentPage}/{pageCount})
              </div>

              <div style={{ marginTop: 8, display: "grid", gap: 8 }}>
                {pageItems.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      onChange(id);
                      setIsOpen(false);
                      setQuery("");
                      setPage(1);
                    }}
                    style={{
                      display: "flex",
                      gap: 8,
                      alignItems: "center",
                      justifyContent: "flex-start",
                    }}
                  >
                    {renderPreview ? renderPreview(id) : null}
                    <span>{id}</span>
                  </button>
                ))}
              </div>

              <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                >
                  Prev
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                  disabled={currentPage >= pageCount}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}