# Dataset and licensing

The dataset manifest is treated as provenance-bearing input, not as model
evidence. The importer preserves `category` and `notes` in separately marked
annotation fields, carries the license string into source metadata, and sets
permission to `unknown` unless the user explicitly changes it. A blank license
is not permission to redistribute or download media.

The manifest importer can associate rows only with a selected account. Existing
local files may be indexed without a remote download; remote media downloads
require `owned` or `authorized`. Users must ensure that any supplied content is
lawfully accessible and that they have the rights and consent needed for their
intended processing. Check YouTube and Instagram terms, copyright, privacy,
and applicable laws before use.

Category labels and notes are excluded from extraction prompts and embedding
inputs. Benchmark ranking disables annotations, and evaluation judgments are
kept outside the manifest and API requests.
