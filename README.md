# getvout website

English-language website for the getvout team in Karnal, Haryana, India.

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
The live custom domain is https://getvout.com; `www` redirects to it.
The old Vercel project remains separate and still serves its other subdomain.

`vercel.json` and `build-vercel.cjs` publish static assets, while `api/index.py`
adapts the local Python handler for pages, RSC navigation, enquiry presets,
image requests and real 404 responses. Local/alternate-host noindex and local-only
forms remain enabled. Vercel authentication protection may require signing in
to view the test deployment.

Do not commit `.vercel/` or `.env.local`; these hold local project/auth state.

- `site-source/` is the canonical, fully local website: paired HTML/React Server Component payloads, compiled JavaScript, CSS, fonts and media.
- `faithful/` is the served build output. The build copies local files byte-for-byte and writes `build-manifest.json`; it never downloads pages or assets.
- This is a compiled snapshot-based implementation, not a conventional editable React source repository. Content changes must keep server HTML, embedded Flight data, `.rsc` payloads and relevant client data consistent. `site_data.py` reads/writes byte-counted Flight records.
- `projects.json` documents the portfolio inventory; changing this inventory alone does not regenerate the rendered pages.
- `journal-content/` contains the articles reviewed and approved by the owner on 24 November 2026. Served sources are in `site-source/en/journal/`.
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
python3 -m unittest test_seo -v
INTERACTIVE=1 SITE_AUDIT=shots/site-browser-audit.json node shots/cdp.js http://localhost:4173/en
```

The static audit checks local targets/assets, route-specific indexing policy, paired payload readability and portfolio counts. Optional `--forbid TEXT` arguments scan website code/content for unwanted legacy terms. The browser audit visits all 23 pages at desktop and mobile sizes and records JavaScript errors, failed responses, broken loaded images, overflow, rendered SEO metadata and unexpected external requests.

## SEO and indexing

- `seo-config.json` is the approved title/description/indexing policy. Run
  `python3 seo_content.py` after updating it, then rebuild and test.
- Twenty canonical URLs are eligible for indexing: Home, Work, Studio, Contact,
  Services and all seven service details, the Journal hub and seven reviewed
  articles. Start Project, Privacy, Imprint and errors remain noindex.
- `robots.txt`, `sitemap.xml` and the community-proposal `llms.txt` are served
  at the domain root. `/llm.txt` redirects to `/llms.txt`.
- Shared Organization/WebSite identities and page-specific structured data are
  present in initial HTML. A small React component keeps JSON-LD correct during
  client-side navigation as the shared layout persists.
- Each of the 23 pages has a custom getvout-branded 1200 × 630 JPEG sharing card
  for Open Graph/Facebook/WhatsApp/LinkedIn and X/Twitter. These use the studio's
  own typography, brand colours and vector artwork, never a client project photo.
- `python3 social_cards.py` regenerates the cards using the local preview server
  at port 4173 and Chrome. It uses no paid image-generation API. The versioned
  card assets are committed, so deployment itself needs no browser.
- Do not invent a sitemap lastmod for routine rebuilds. Journal publication
  dates reflect the owner's approval; change dates only for real content changes.
- The Google Search Console verification tag is included in every page's
  `<head>`. A Domain property also requires the same token as a DNS TXT record
  at the third-party DNS host; Vercel does not manage this domain's DNS.
- Search Console verification and sitemap submission remain separate steps.
  No indexation, ranking, Google sitelinks or AI citations are guaranteed.
- Indexing guidance is not a model-training licence. No bespoke AI-training
  policy or draft Content-Signal directives were introduced.

## Analytics

- Vercel Web Analytics is enabled on the `getvout-website` project. The
  cookie-free loader is injected into every page's `<head>` by `seo_content.py`.
- Local previews serve a no-op `/_vercel/insights/script.js`; Vercel serves the
  real script in production. Page views and referrers appear in the Vercel
  dashboard.
- `404.html` includes the same loader so missing routes can be measured.
- The privacy notice describes Vercel Web Analytics and remains a draft pending
  final legal review.

## Preview limitations

- Production indexing was authorized on 24 November 2026. Local/alternate deployment hosts still emit noindex response headers; unfinished pages and 404s remain noindex.
- Forms validate locally and do **not** deliver enquiries; the interface says so.
- Analytics are enabled in production; local previews use a no-op stub and send nothing.
- Journal articles disclose AI assistance and the owner's confirmed team review, and retain source links.
- Privacy and Imprint remain drafts pending confirmed legal/business details and production service arrangements.
- Third-party/client content and media rights must be verified before public release.
- SEO skills are installed in the parent workspace `.opencode/`; see `.opencode/SEO-INSTALL.md`. No credentials, paid integrations, search submissions or public ranking measurements were used.
