# Local Job Queue

Capture job vacancies instantly and let a local Ollama model process them in the background. The job page is safely stored in SQLite before the extension reports success, so you can immediately continue to the next vacancy.

## Components

- **Job Queue Capture extension**: reads the rendered page you already have open and submits it to localhost. It does not wait for Ollama.
- **Local FastAPI application**: owns the queue, SQLite database, dashboard, editing, retry, and export.
- **Ollama worker**: processes one queued vacancy at a time to avoid competing for GPU memory.
- **Grounded AI chat**: uses `nomic-embed-text:latest` for semantic retrieval and your chat model for cited answers.

Everything stays on your computer.

## Windows installation

Prerequisites: Python 3.11–3.14, Node.js LTS, and Ollama. Your existing `ministral-3:3b` model is the default.

1. Extract the ZIP to a permanent folder, for example `Documents\LocalJobQueue`.
2. Start Ollama normally. Test <http://127.0.0.1:11434/api/tags> in a browser.
3. Double-click `run_windows.bat`. The first launch installs the Python and React dependencies and builds the dashboard.
4. Leave the terminal open. The React dashboard opens at <http://127.0.0.1:8765>.
5. Open `chrome://extensions`, enable **Developer mode**, and choose **Load unpacked**.
6. Select the extracted `extension` folder—not the project root.
7. Pin **Job Queue Capture** to the Chrome toolbar.

No `OLLAMA_ORIGINS` setting is required for this version: only the local Python application talks to Ollama.

The sidebar provides Overview, Pipeline, Jobs, Add Jobs, AI Assistant, and Profile pages. FastAPI serves both the React build and the capture API on port 8765.

## Daily use

1. Start Ollama.
2. Double-click `run_windows.bat`.
3. Open a vacancy and click **Job Queue Capture → Add to queue**.
4. Move to the next vacancy as soon as **Saved to queue ✓** appears.
5. Review results later in the dashboard.

The dashboard refreshes the queue automatically. Re-capturing the same URL updates its stored page and returns it to the queue instead of creating a duplicate.

## Changing the React design

React source files are under `frontend\src`. After editing them, run `build_frontend.bat`, then restart `run_windows.bat`. The launcher also rebuilds the frontend automatically each time it starts. Backend Python changes require only an application restart.

The packaged database already contains the 30 unique jobs from the two JSON exports supplied with this project. Use **Import JSON** for later exports; both the queue export format and the earlier flat tracker format are supported.

## Queue statuses

- `queued`: safely stored and waiting
- `processing`: currently being analyzed by Ollama
- `completed`: structured tracker record is ready
- `failed`: page remains stored; inspect the message and press Retry

Jobs left in `processing` during a shutdown are automatically returned to `queued` on the next launch.

## Tracker data

The generated record includes company, role, application status, dates, URL, location/format, employment type, salary, sponsorship, requirements, technologies, evidence, full archived description, CV version, portfolio item, core competency, referral, contact dates, next action, and notes.

The page itself cannot know which CV or portfolio you submitted, so those strategy fields remain editable in the dashboard.

Use **Export CSV** for spreadsheets and **Export JSON** for backups or a future dashboard migration. The SQLite database is at `data\jobs.db`.

## Change the model

The default model is `ministral-3:3b`. To use another installed model, add this before the final Python command in `run_windows.bat`:

```bat
set JOB_QUEUE_MODEL=llama3.2:3b
```

`nomic-embed-text` is an embedding model, so it is not used for JSON extraction. The dashboard uses it for semantic retrieval in grounded chat. The first question can take longer because embeddings are generated and cached; subsequent questions reuse them.

## Troubleshooting

- If the application does not start, run `run_windows.bat` again. The fixed launcher now stays open on errors. Send a screenshot containing the first error lines, not only the final `STARTUP FAILED` message.
- **`pydantic-core` / PyO3 says Python 3.14 is too new**: you are running an older package pinned to Pydantic 2.11.7. Use the updated package, whose Python 3.14-compatible Pydantic release installs from a prebuilt wheel instead of compiling Rust.
- If you replace only individual files in an existing folder, delete that folder's `.venv` once and run `run_windows.bat` again. A newly extracted copy does not need this cleanup.
- Run `diagnose_windows.bat` to check Python, Node.js, npm, Ollama, port 8765, and the required project files.
- **Start the local Job Queue app first**: `run_windows.bat` is not running or port 8765 is unavailable.
- **Connection refused in a failed job**: Ollama is not running on port 11434.
- **Model not found**: confirm the spelling using `ollama list`, then adjust `JOB_QUEUE_MODEL`.
- **Incomplete job description**: expand any “show more” section before capture.
- **Protected browser page**: extensions cannot run on `chrome://` pages or the Chrome Web Store.

Do not store real passwords in tracker fields. If you use a portal hint, keep it non-sensitive.
