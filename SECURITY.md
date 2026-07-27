# πX Technologies — Security Notice

## Exposed credentials

During early development, the following credentials were committed to this repository's history:

- Supabase project URL and anon key
- Gemini API key
- Stitch API key

These credentials appear in old commits and must be considered compromised.

## Required actions

1. **Rotate all affected keys immediately** in the respective service dashboards:
   - Supabase: Project Settings → API → Rotate anon/service role keys.
   - Google AI Studio: Regenerate the Gemini API key.
   - Stitch: Regenerate the project API key.
2. **Never commit `.env` or `.env.production` to git.** Use `.env.example` as a template.
3. **For full removal from git history**, use `git filter-repo` or BFG Repo-Cleaner. This rewrites history and must be coordinated with the team.

## Secret handling policy

- Store production secrets in a secrets manager (e.g., GitHub Secrets, AWS Secrets Manager, Doppler).
- Use `.env.production` only for local deployment testing; do not commit it.
- Keep service-role keys on the backend only; never expose them in the browser.
