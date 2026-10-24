# Phase 0 fixtures

The fixture set contains three scenario definitions, one graph per scenario, and
one completed run for every scenario/mode pair (six completed runs total).

The frontend defaults to the live API. Set `VITE_USE_MOCKS=true` explicitly to
use these files. Keep it `false` (or unset) and provide `VITE_API_URL` to use
the backend without changing UI code.
