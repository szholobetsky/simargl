---
title: "simargl: Task-to-Code Retrieval via Semantic Similarity over Git History"
authors:
  - name: Stanislav Zholobetskyi
    orcid: 0009-0008-6058-7233
    affiliation: 1
affiliations:
  - name: Institute for Information Recording, Kyiv, Ukraine
    index: 1
date: 2026-04-14
bibliography: paper.bib
---

# Summary

`simargl` is a Python library and command-line tool for task-to-code retrieval: given a natural language description of a software change (a task, bug report, or feature request), it identifies which source files and modules are most likely to require modification. The tool builds a semantic index over historical git commits and linked task tracker records, then answers queries using dense vector similarity. It exposes both a CLI and an MCP (Model Context Protocol) server, making it suitable for integration with AI coding agents.

# Statement of need

When a developer starts work on a new task, locating the relevant code is often the first and most time-consuming step, particularly in large or unfamiliar codebases. Keyword search over file contents is fast but brittle: it requires exact term matches and fails when business vocabulary diverges from code identifiers. Manual navigation relies on familiarity that new team members and AI assistants lack.

A promising alternative is to learn from history: if similar tasks in the past touched a particular module, a new similar task likely will too. This insight underlies information-retrieval approaches to bug localization [@zhou2012should; @saha2013improving], but existing tools in this space are research prototypes not designed for practical deployment, do not expose programmatic APIs, and do not support modern dense embedding models.

`simargl` fills this gap. It is designed to run on a developer's laptop, indexes any git repository with or without a task tracker, supports a range of embedding models from lightweight CPU-friendly ones to high-accuracy GPU models, and serves results through an MCP interface that any AI agent can call directly during a coding session.

# Functionality

**Indexing** (`simargl index files`, `simargl index units`): the tool extracts commits and optionally linked task descriptions from a SQLite database, encodes them as dense vectors using a configurable sentence-transformer model, and stores the index locally. Incremental updates track file modification times and avoid re-embedding unchanged content.

**Search** (`simargl search`): a query is encoded with the same model and compared against the index using cosine similarity. Three search modes are supported: file-level retrieval, module-level aggregation, and combined scoring.

**Ingest pipeline** (`simargl init`, `simargl ingest`): a wizard creates a project configuration file and an incremental ingestion pipeline extracts commits from git and fetches task details from Jira, GitHub Issues, YouTrack, or GitLab via pluggable connectors. A checkpoint mechanism allows resuming interrupted ingestion.

**MCP server** (`simargl serve`): exposes `index_files`, `index_units`, `search`, `status`, and `vacuum` as MCP tools, enabling AI agents to query the retrieval system as part of an automated coding workflow.

**Evaluation**: on the SonarQube dataset (9,799 tasks, 12,532 files), `simargl` with the `bge-large-en-v1.5` model achieves MAP@10 = 0.371 at the file level. Experiments across five embedding model families confirm that general-purpose sentence transformers consistently outperform code-specific models such as CodeBERT [@feng2020codebert] on this task.

# Related software

`Locus` [@wen2016locus] and `BLUiR` [@saha2013improving] are academic bug localization systems but are not maintained, require specific input formats, and do not expose APIs. `codesearchnet` [@husain2019codesearchnet] addresses code search from natural language but does not use commit history. No existing open tool provides a deployable, history-based, embedding-powered retrieval system with an MCP interface.

# Acknowledgements

This work is conducted as part of a PhD research programme at the Institute for Information Recording, Kyiv, Ukraine.

# References
