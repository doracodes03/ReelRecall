import Button from '../common/Button';
import Modal from '../common/Modal';

export default function BulkReindexDialog({
  open,
  total,
  busy,
  onClose,
  onConfirm,
}: {
  open: boolean;
  total: number;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Modal
      open={open}
      onClose={() => {
        if (!busy) onClose();
      }}
      title="Re-index all saved videos?"
      description={`This will queue ${total} ${total === 1 ? 'video' : 'videos'} in your library for content extraction and indexing. Processing may take time. Existing indexed content may be refreshed according to the indexing pipeline. Media downloads still follow each video's permission setting.`}
    >
      <div className="flex flex-col-reverse justify-end gap-3 pt-1 sm:flex-row">
        <Button variant="ghost" disabled={busy} onClick={onClose}>Cancel</Button>
        <Button disabled={busy || total === 0} onClick={onConfirm}>
          {busy ? 'Queueing videos…' : 'Confirm re-index'}
        </Button>
      </div>
    </Modal>
  );
}
