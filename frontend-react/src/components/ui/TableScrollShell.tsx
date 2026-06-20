import {
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
  type UIEvent,
} from "react";

interface TableScrollShellProps {
  children: ReactNode;
  className?: string;
}

export function TableScrollShell({ children, className }: TableScrollShellProps) {
  const topScrollRef = useRef<HTMLDivElement>(null);
  const bodyScrollRef = useRef<HTMLDivElement>(null);
  const spacerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const syncingRef = useRef(false);

  const syncSpacerWidth = useCallback(() => {
    const table = tableRef.current;
    const spacer = spacerRef.current;
    if (!table || !spacer) {
      return;
    }
    spacer.style.width = `${table.scrollWidth}px`;
  }, []);

  useEffect(() => {
    syncSpacerWidth();
    const table = tableRef.current;
    if (!table) {
      return;
    }
    const observer = new ResizeObserver(() => {
      syncSpacerWidth();
    });
    observer.observe(table);
    return () => observer.disconnect();
  }, [syncSpacerWidth]);

  function syncScrollLeft(source: "top" | "body", event: UIEvent<HTMLDivElement>) {
    if (syncingRef.current) {
      return;
    }
    syncingRef.current = true;
    const nextLeft = event.currentTarget.scrollLeft;
    if (source === "top" && bodyScrollRef.current) {
      bodyScrollRef.current.scrollLeft = nextLeft;
    } else if (source === "body" && topScrollRef.current) {
      topScrollRef.current.scrollLeft = nextLeft;
    }
    syncingRef.current = false;
  }

  return (
    <div className={["table-scroll-shell", className].filter(Boolean).join(" ")}>
      <div
        ref={topScrollRef}
        className="table-scroll-x table-scroll-x--top"
        aria-hidden="true"
        onScroll={(event) => syncScrollLeft("top", event)}
      >
        <div ref={spacerRef} className="table-scroll-x__spacer" />
      </div>
      <div
        ref={bodyScrollRef}
        className="table-wrap"
        onScroll={(event) => syncScrollLeft("body", event)}
      >
        <table ref={tableRef} className="data-table">
          {children}
        </table>
      </div>
    </div>
  );
}
