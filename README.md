# getvout website

Local English-language website for the getvout team in Karnal, Haryana, India.

## Preview

```sh
python3 build_local.py
python3 serve.py
```

Open http://localhost:4173/en.

The preview/build use Python's standard library. For content-editing and audit
tools, install `python3 -m pip install -r requirements-build.txt` in a virtual
environment.

## Source and build

### Vercel

The GitHub repository is connected to the separate Vercel project
`getvout-website` in `rishavs-projects-e5cac2c2`.
Its initial test URL is https://getvout-website.vercel.app.
The existing custom domain has not been transferred.

`vercel.json` and `build-vercel.cjs` publish static assets, while `api/index.py`
adapts the local Python handler for pages, RSC navigation, enquiry presets,
image requests and real 404 responses. Preview noindex and local-only forms
remain enabled. Vercel authentication protection may require signing in to
view the test deployment.

Do not commit `.vercel/` or `.env.local`; these hold local project/auth state.

- `site-source/` is the canonical, fully local website: paired HTML/React Server Component payloads, compiled JavaScript, CSS, fonts and media.
- `faithful/` is the served build output. The build copies local files byte-for-byte and writes `build-manifest.json`; it never downloads pages or assets.
- This is a compiled snapshot-based implementation, not a conventional editable React source repository. Content changes must keep server HTML, embedded Flight data, `.rsc` payloads and relevant client data consistent. `site_data.py` reads/writes byte-counted Flight records.
- `projects.json` documents the portfolio inventory; changing this inventory alone does not regenerate the rendered pages.
- `journal-content/` contains editorial draft material. The published preview sources are in `site-source/en/journal/`.
- `legal-content/` contains legal draft fragments. After editing, run `python3 sync_legal.py`, then rebuild.
- `shots/cdp.js` is the browser test harness. It uses a separate temporary Chrome profile and closes its own browser after testing.
- Generated output, screenshots, logs, local environments and agent/skill tooling are excluded from Git. All assets needed to rebuild the website are included in `site-source/`.
- Previous download/adaptation scripts, obsolete source snapshots, unused project media and historical reference captures have been removed.

## Content rules

- Home: four cards—JAC Creation, Hira Dhan Builders, Rudra Infocom, Bloom—with an All work link.
- Work: all eight selected projects. JAC Creation is first/default menu preview; Rudra Infocom is third; TalScout.ai is last.
- Studio: 20+ overall projects, eight selected projects, seven services, one team.
- No service prices; discuss requirements, scope, timeline and a tailored proposal.
- English only. Theme controls, interactions and animations remain available.
- Sound defaults on each fresh document visit; visitors can mute it. Browser autoplay rules can require an interaction before audio plays.
- Email: hello@getvout.com and contact@getvout.com.
- +91 7404511743 is **WhatsApp-only**: https://wa.me/917404511743.
- Official socials: https://www.linkedin.com/company/getvout/ and https://www.instagram.com/getvout.
- Unknown routes return a local 404. No remote website fallback or asset proxy.

## Audit

```sh
python3 audit_site.py
INTERACTIVE=1 SITE_AUDIT=shots/site-browser-audit.json node shots/cdp.js http://localhost:4173/en
```

The static audit checks local targets/assets, preview indexing controls, paired payload readability and portfolio counts. Optional `--forbid TEXT` arguments scan website code/content for unwanted legacy terms. The browser audit visits all 23 pages at desktop and mobile sizes and records JavaScript errors, failed responses, broken loaded images, overflow and unexpected external requests.

## Preview limitations

- Pages remain `noindex, follow`. Do not enable public indexing or deploy without authorization.
- Forms validate locally and do **not** deliver enquiries; the interface says so.
- Analytics remain disabled.
- Journal articles are visibly labelled AI-assisted editorial drafts with source links; human review is required before publication.
- Privacy and Imprint remain drafts pending confirmed legal/business details and production service arrangements.
- Third-party/client content and media rights must be verified before public release.
- SEO skills are installed in the parent workspace `.opencode/`; see `.opencode/SEO-INSTALL.md`. No credentials, paid integrations, search submissions or public ranking measurements were used.
