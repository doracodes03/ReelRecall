import { useState, type FormEvent } from 'react';
import Button from '../common/Button';
import Modal from '../common/Modal';
import { saveVideo } from '../../services/videos';

export default function SaveVideoDialog({ onSaved }: { onSaved?: () => unknown }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [permissionStatus, setPermissionStatus] = useState<'unknown' | 'owned' | 'authorized'>('unknown');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const savedVideo = await saveVideo(url, permissionStatus);
      setUrl('');
      setPermissionStatus('unknown');
      setOpen(false);
      setSuccess(
        savedVideo.status === 'queued' || savedVideo.status === 'processing'
          ? 'Video saved. Content indexing has been queued.'
          : 'Video is already in your library.',
      );
      try {
        await onSaved?.();
      } catch {
        setError('The video was saved, but the library could not refresh. Reload to see it.');
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to save this video.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Button
        className="min-h-12 rounded-full px-6"
        onClick={() => {
          setError('');
          setSuccess('');
          setOpen(true);
        }}
      >
        <span aria-hidden="true" className="text-xl leading-none">+</span>
        Save a video
      </Button>
      {success && <p role="status" className="mt-3 text-sm font-medium text-emerald-800">{success}</p>}
      {error && !open && <p role="alert" className="mt-2 text-sm text-rose-800">{error}</p>}
      <Modal
        open={open}
        onClose={() => {
          if (!saving) setOpen(false);
        }}
        title="Save a video"
        description="Add a YouTube Short or Instagram Reel to your private library."
      >
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label htmlFor="video-url" className="mb-2 block text-sm font-bold text-[var(--rr-text)]">Video URL</label>
            <input
              id="video-url"
              type="url"
              required
              autoFocus
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://www.youtube.com/shorts/…"
              className="min-h-12 w-full rounded-xl border border-[var(--rr-border)] bg-white px-4 py-3 text-base text-[var(--rr-text)] placeholder:text-[var(--rr-muted)] focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
            />
          </div>
          <div>
            <label htmlFor="media-permission" className="mb-2 block text-sm font-bold text-[var(--rr-text)]">Media permission</label>
            <select
              id="media-permission"
              value={permissionStatus}
              onChange={(event) => {
                const value = event.target.value;
                if (value === 'unknown' || value === 'owned' || value === 'authorized') {
                  setPermissionStatus(value);
                }
              }}
              className="min-h-12 w-full rounded-xl border border-[var(--rr-border)] bg-white px-4 py-3 text-base text-[var(--rr-text)] focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
            >
              <option value="unknown">Unknown — do not download media</option>
              <option value="owned">I own this media</option>
              <option value="authorized">I am authorized to process it</option>
            </select>
            <p className="mt-2 text-xs leading-5 text-[var(--rr-muted)]">Media is downloaded for content extraction only when you confirm you own it or are authorized to process it.</p>
          </div>
          {error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}
          <div className="flex flex-col-reverse justify-end gap-3 pt-1 sm:flex-row">
            <Button variant="ghost" disabled={saving} onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={saving || !url.trim()}>
              {saving ? 'Saving…' : 'Add to library'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
