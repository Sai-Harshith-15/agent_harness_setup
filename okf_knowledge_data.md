Open Knowledge Format (OKF)
📖 Read the Open Knowledge Format v0.1 specification → SPEC.md
This repository is primarily about the Open Knowledge Format (OKF).

OKF is a universal, vendor-neutral format for representing knowledge as plain markdown files with YAML frontmatter. It is not tied to any particular agent, framework, model provider, or serving system. The goal is simple:

Anyone can produce OKF — humans authoring by hand, agents built on any framework (Google ADK, LangChain, custom), export pipelines from existing catalogs (Dataplex, Unity Catalog, Collibra, …), or scripts walking a database.
Anyone can serve and consume OKF — a static file server, a knowledge-management UI (Obsidian, Notion, MkDocs), an LLM loading files into context, a search index, or a graph viewer like the one bundled in this repo.
The agent below is a proof of concept demonstrating one way to produce OKF bundles automatically. The format itself is the contribution; this agent and the visualizer exist to make the format tangible at both ends — production and consumption.

See OKF in practice — three ready-to-browse bundles produced by this agent, checked into bundles/:

bundles/ga4/ — GA4 e-commerce dataset (viz.html)
bundles/stackoverflow/ — Stack Overflow public dataset (viz.html)
bundles/crypto_bitcoin/ — Bitcoin blocks/transactions (viz.html)
Why OKF?
OKF represents catalog knowledge as plain markdown files with YAML frontmatter, organized in a directory hierarchy. That choice unlocks a few properties that are hard to get from a service-owned metadata store:

Human- and agent-readable. No SDK or query language stands between a reader and the content. An engineer can cat a concept; an LLM can ingest it verbatim into context.
Version-controllable out of the box. Bundles live in git. Pull requests, line-by-line diffs, blame, and review workflows just work — knowledge curation becomes a normal software-engineering activity.
Portable and lock-in free. A bundle is a directory. Ship it as a tarball, host it in any repo, mount it from any filesystem, or sync it to any system that speaks files. No proprietary API stands between you and your metadata.
Mixes structured and unstructured data deliberately. Use frontmatter for the few fields you want to query, filter, or index on (type, resource, tags, timestamp); use the markdown body for the prose, schemas, and example queries that LLMs and humans actually read.
Minimally opinionated, freely extensible. A small set of required keys ensures interoperability, but bundles can carry arbitrary extra frontmatter keys and arbitrary body sections without breaking consumers.
Composes with existing tooling. Many knowledge tools — Notion, Obsidian, MkDocs, Hugo, Jekyll — already speak markdown plus YAML frontmatter, so bundles can be browsed, edited, or rendered without custom UI.
Progressive disclosure built in. Auto-generated index.md files let an agent or human navigate the hierarchy one level at a time instead of loading the entire bundle into context.
Graph-shaped, not just tree-shaped. Concepts link to each other via normal markdown links, expressing relationships richer than the parent/child implied by the directory layout.
The net effect is that reference agents, consumption agents, and humans collaborate on the same artifacts in the same way they already collaborate on source code.

Install
python3.13 -m venv .venv
.venv/bin/pip install --index-url https://pypi.org/simple/ -e .[dev]
Credentials
BigQuery: gcloud auth application-default login plus a project for billing (gcloud config set project <id>). Public datasets are readable, but the caller's project is billed for query bytes.
Gemini: set GEMINI_API_KEY (AI Studio) or use Vertex AI by setting GOOGLE_GENAI_USE_VERTEXAI=true, GOOGLE_CLOUD_PROJECT=<id>, and GOOGLE_CLOUD_LOCATION=<region>.
How the reference agent works
The reference agent runs in two passes. The BQ pass writes one OKF doc per concept the source advertises, using BigQuery metadata alone. The web pass then runs the LLM as its own crawler: it receives a list of seed URLs (provided via --web-seed or --web-seed-file), fetches the seeds via the fetch_url tool, and decides which outbound links are worth following based on whether they look like authoritative documentation for the existing concepts. For each page it fetches, the agent chooses to (a) enrich one or more existing concept docs, (b) mint a standalone references/<slug> doc, or (c) skip. A hard --web-max-pages cap and a same-domain allowed-hosts filter (configurable via --web-allowed-host) are enforced inside the tool, so the agent cannot overrun. Use --no-web to skip the web pass.

Run
Minimum invocation — point at a BigQuery dataset and a bundle output directory. Seeds for the web pass are explicit; omit them (or pass --no-web) to run BQ-only:

.venv/bin/python -m reference_agent enrich \
    --source bq \
    --dataset <project>.<dataset> \
    --web-seed-file <path/to/seeds.txt> \
    --out ./bundles/<name>
Iterate on a single concept by adding --concept <type>/<name> (e.g. --concept tables/events_); repeatable.

Samples
Each sample pairs a recipe (samples/<name>/, with the seed URLs and exact enrich command) with the produced bundle (bundles/<name>/) that the recipe generated. Open the recipe to reproduce; open the bundle to browse the result directly.

GA4 Google Merchandise Store — public e-commerce dataset, seeded with canonical GA4 BigQuery Export documentation URLs. · recipe · bundle · viz.html
Stack Overflow — public dataset (mirror of the Stack Exchange Data Dump), seeded with the community's canonical schema references. Exercises multi-concept enrichment from cross-cutting docs pages. · recipe · bundle · viz.html
Bitcoin (crypto) — public dataset (blocks, transactions, inputs, outputs) from the bitcoin-etl pipeline. Exercises cross-table foreign-key relationships in prose. · recipe · bundle · viz.html
Visualize
The visualize subcommand renders any OKF bundle as a self-contained interactive HTML file — one file, no backend, no install on the viewing side. Open it in any modern browser, share it as an artifact, host it on a static file server, or commit it next to the bundle (as this repo does).

The viewer is itself a proof-of-concept consumer of OKF, mirroring the way the reference agent is a proof-of-concept producer. OKF bundles can be consumed by anything that reads markdown; this is just one shape.

What it shows
A force-directed graph of every concept in the bundle, with colored nodes by type (datasets, tables, references, …) and directed edges drawn from each cross-link in the markdown bodies.
A detail panel for the selected concept showing its frontmatter (description, resource link, tags) and its rendered markdown body — with internal […](/path/to/concept.md) links rewired to navigate within the viewer instead of following the path.
A "Cited by" backlinks list under each concept (computed from the reverse of the link graph).
A search box (matches title, concept id, and tags), a type filter, and switchable graph layouts (cose / concentric / breadth-first / circle / grid).
Generate
.venv/bin/python -m reference_agent visualize --bundle ./bundles/<name>
That writes bundles/<name>/viz.html. Flags:

Flag	Default	Description
--bundle	(required)	Bundle root directory.
--out	<bundle>/viz.html	Output HTML path.
--name	bundle directory name	Display name shown in the viewer header.
Example, writing the output somewhere else and overriding the header:

.venv/bin/python -m reference_agent visualize \
    --bundle ./bundles/crypto_bitcoin \
    --out /tmp/btc.html \
    --name "Bitcoin OKF"
How it's built
The HTML embeds the bundle as a JSON blob and uses Cytoscape.js for the graph and marked for in-browser markdown rendering, both loaded from a CDN. No data leaves the page; the bundle is parsed once at generation time and serialized into the file.

Tests
.venv/bin/pytest



r&d data:

Setting up Google's Open Knowledge Format (OKF) at the project level is one of the highest-leverage ways to make your codebase natively understood by AI agents. Introduced by Google Cloud in June 2026, OKF isn't a complex software installation or a proprietary database. It is a minimalist, open specification that uses standard Markdown files with YAML frontmatter to bridge the gap between human-readable wikis and agent-parseable data.  By implementing this, you give your AI tools (like Gemini, Claude Code, or custom RAG pipelines) direct access to your project's context—architectures, schemas, runbooks, and business rules—without requiring bespoke SDKs or vendor lock-in.  Here is a detailed, step-by-step guide to architecting OKF within your project.1. Initialize the Knowledge "Bundle"In OKF terminology, a bundle is the root directory that holds your knowledge. Because OKF is designed to live directly alongside the code it describes, you should create this inside your project repository.  Create the directory: At your project root, create a dedicated folder. Common conventions are okf/, knowledge/, or docs/okf/.Create the index.md: This is a reserved filename in the OKF spec. Place it at the root of your bundle (e.g., okf/index.md). It acts as the primary entry point, summarizing the repository's layout for both agents and human developers.  2. Define Your "Concepts" (The Markdown Files)Every file in an OKF bundle represents a single concept. A concept can be a tangible technical asset (like an API endpoint or a database table) or an abstract idea (like a deployment playbook, an engineering standard, or a metric definition).  The file path itself serves as the concept's identity. Organize them logically within your bundle.  Example file structure:Plaintextyour-project/
└── okf/
    ├── index.md
    ├── architecture-overview.md
    ├── database/
    │   ├── users-table.md
    │   └── payments-table.md
    └── runbooks/
        └── deployment-guide.md
3. Add the YAML Frontmatter (The Core of OKF)What separates an OKF file from a standard documentation file is the YAML metadata at the very top. The OKF v0.1 specification requires exactly one field—type—but recommends a few others for maximum interoperability.  Here is exactly how a concept file (e.g., users-table.md) should look:YAML---
type: database_table
title: Users Core Table
description: The primary table storing user authentication and profile data.
resource: uri://my-database/schema/users
tags: [backend, core, auth]
timestamp: 2026-07-05T09:00:00Z
---

# Users Table
The `users` table is the source of truth for all account identities...
Key Frontmatter Fields:type (Required): Defines what the concept is (e.g., api, table, metric, playbook). OKF is minimally opinionated, meaning you define the taxonomy; the spec doesn't force a specific list on you.  title: A human-readable display name.description: A 1-2 sentence summary. Agents use this heavily for semantic search, previews, and indexing.resource: A URI identifying the actual technical asset (if applicable).tags: An array of strings for cross-cutting categorization.timestamp: The last time the knowledge was meaningfully updated. It must be in ISO 8601 format.  4. Wire It Together With Cross-LinksAgents reason better when they understand how systems relate to one another. You can link your OKF documents together using standard Markdown links.  OKF supports two linking styles, but absolute linking is highly recommended:  Absolute Links (Bundle-Relative): These start with a / and are evaluated from the root of your OKF directory. They are stable and won't break if you move files into different subdirectories later.Example: See the [Payments Table](/database/payments-table.md) for billing details.Relative Links: Standard markdown relative paths.  Example: See the [Payments Table](./payments-table.md).Note: The markdown link itself just establishes a connection. It is best practice to explain the relationship in the surrounding text (e.g., "The Users table joins with the [Payments Table] on user_id").  5. Establish an Audit Trail with log.mdIf your project requires compliance, or if you simply want agents to understand the history of architectural decisions, OKF reserves the filename log.md.You can place a log.md in any directory to maintain a chronological ledger of changes for that specific area of the project. It acts as an audit trail that agents can read to understand why a system behaves the way it does today, rather than just how it works.6. Integrate with Your AI AgentsOnce your OKF bundle is committed to version control, it is immediately usable.For local coding agents, simply point the agent's workspace to your repository. Because the format is plain text, the agent will automatically ingest the frontmatter and markdown context. For larger enterprise setups, you can point your ingestion scripts directly at the okf/ directory. The structured YAML provides your embedding models with perfect metadata to chunk and index, which drastically reduces AI hallucinations.  Implementation Best Practices  To get the most out of OKF, treat this knowledge exactly like code. OKF bundles should go through the same Pull Request and code review processes as your actual software. If an engineer updates a database schema, they should be expected to update the corresponding OKF file in the same PR. Start small by documenting the one table or runbook that currently confuses your AI tools the most, ensure your team agrees on a standard list for the type field, and expand from there. Keeping this knowledge version-controlled alongside your code ensures that as your project evolves, your AI agents' understanding scales right alongside it.  

