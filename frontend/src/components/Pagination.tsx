interface Props {
  page: number;
  totalPages: number;
  totalItems: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, totalItems, onPageChange }: Props) {
  if (totalItems === 0) return null;
  return (
    <div className="pagination" aria-label="Telemetry pagination">
      <span>Showing page {page} of {totalPages}</span>
      <div className="pagination-buttons">
        <button className="button button-quiet" type="button" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>Previous</button>
        <button className="button button-quiet" type="button" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>Next</button>
      </div>
    </div>
  );
}
