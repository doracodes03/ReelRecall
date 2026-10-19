import { useEffect, useRef } from 'react';

type ModalProps = {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  description?: string;
};

export default function Modal({ title, open, onClose, children, description }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const descriptionId = `${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-description`;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="rr-dialog"
      aria-labelledby={`${descriptionId}-title`}
      aria-describedby={description ? descriptionId : undefined}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="rr-dialog-panel">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 id={`${descriptionId}-title`} className="text-xl font-extrabold tracking-tight text-[var(--rr-text)]">{title}</h2>
            {description && <p id={descriptionId} className="mt-2 text-sm leading-6 text-[var(--rr-muted)]">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="grid size-10 shrink-0 place-items-center rounded-full border border-[var(--rr-border)] text-xl text-[var(--rr-muted)] transition hover:bg-[var(--rr-lavender)] hover:text-[var(--rr-purple)]"
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
