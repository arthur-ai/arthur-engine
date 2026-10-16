# Vercel

HTTP connector proposed in arthur-engine #2433.

- Fixed public host: no URL field, no must-be-https field and no TLS fields in the catalog.
- `address.instance` is the team id; `address.scope` is `"global"` (Vercel has no region).
- Least privilege: a team token with the Viewer role.
- Page cap: 100 pages.
- `service_names` is left unset on purpose: project names are short and not unique across a customer's services.
- The include list reuses `discovery/endpoint/scope.py:parse_group_names` (imported, not copied).
- Test bodies are built from Vercel's published SDK models; keep availability preview until a live account has been scanned.
