---
name: audio-course
description: >
  Build a passive audio course (or an audiobook of a free public book) and
  deliver it to the user's podcastfeeds Learning feed. Use when the user says
  "make me an audio course on X", "audio tutorial about X", "teach me X as a
  podcast", "turn this book into an audiobook", "put X in my podcast feed as a
  course", or points at a free online book and wants to listen to it.
---

# Audio course

A hands-free course for listening on a commute. Unlike teach-tech, never stop
for the listener to type anything: everything is taught by explanation,
analogy and repetition. Code goes in show notes.

## 1. Classify

- A **topic** goes to the course path.
- A **book** (a URL, or a title with a free official online edition) gets a
  choice via AskUserQuestion: "Audiobook (the author's text, one episode per
  chapter)" or "Course about it". Only offer the audiobook when the full text
  is freely and officially published online.

## 2. Course path

1. **Clarify** with one AskUserQuestion call (up to three questions,
   multiple choice): why they want to learn it, which aspects matter, what they
   already know. Check what they usually work with (their CLAUDE.md, the
   current repo) to pick analogies.
2. **Research** with web search: current best practice and facts you would
   otherwise state from memory.
3. **Size and outline.** One episode for a narrow topic, up to 8 parts of 15 to
   20 minutes (about 2200 to 3000 spoken words) for a broad one. Show: course
   title, language (`da` or `en`, ask if unclear), and per part a title plus
   one line on what the listener will understand afterwards. **Stop and wait
   for an explicit yes.** Loop on edits.
4. **Write each part for the ear:**
   - flowing spoken prose; no markdown, lists, tables, headings or URLs
   - describe code in words ("a function that borrows the string and returns
     its length"); never read symbols out
   - open with a two-sentence recap of the previous part (from part 2 on)
   - close with a short summary of the part's key ideas
   - use analogies from the listener's own stack
   - put snippets and source links in `show_notes_md` (markdown: fenced code,
     inline code, `[text](https://...)` links, `- ` bullets)
   - do not add a title line or a sign-off; the server adds "X, part 2 of 4:
     Y." and "Next up: part 3."
   - each script must be 200 to 60000 characters (a 15 to 20 minute part is
     roughly 13000 to 18000)

## 3. Audiobook path

1. Fetch the table of contents. Show the chapter list, marking front matter and
   appendices in or out, and whether each chapter goes as a **URL** (the book
   has a page per chapter; preferred, the server extracts text and images
   itself) or as **verbatim text** (the whole book is one page: split it by
   chapter heading and send each chapter as `script` with `"verbatim": true`,
   unchanged). **Stop and wait for an explicit yes.**
2. Cap: 60 chapters.
   Title each part with the book's own label, because the server announces
   the title as given ("Shape Up: Chapter 1: Introduction.") and ends with
   "End of <title>.": e.g. "Foreword by Jason Fried", "Chapter 1:
   Introduction", "Chapter 2: Principles of Shaping". Never rely on the part
   number for chapter numbering; front matter shifts it.
3. Every `script` must be 200 to 60000 characters, or the server rejects the
   whole request. Merge a short piece (dedication, epigraph) into its
   neighbour or leave it out, and split an over-long chapter into "Chapter 7,
   part 1" and "Chapter 7, part 2". Say so in the chapter list you show.

## 4. Submit

1. Build the request and save it before sending, so nothing is lost if the
   server is down:

   ```bash
   mkdir -p ~/.cache/audio-course
   # write ~/.cache/audio-course/<course_id>.json with:
   # {"course_id": "<a-z0-9- slug, e.g. rust-ownership-2026-09-30>",
   #  "title": "...", "kind": "course" | "audiobook", "language": "en" | "da",
   #  "episodes": [{"part": 1, "title": "...", "script": "...",
   #                "show_notes_md": "..."} | {"part": 1, "title": "...",
   #                "url": "https://..."}]}
   ```

2. Send it:

   ```bash
   URL="${PODCASTFEEDS_URL:?set PODCASTFEEDS_URL}"
   TOKEN="${PODCASTFEEDS_TOKEN:-$(cat "${PODCASTFEEDS_TOKEN_FILE:?set PODCASTFEEDS_TOKEN or PODCASTFEEDS_TOKEN_FILE}")}"
   curl -sS --fail-with-body -X POST "$URL/$TOKEN/api/course" \
     -H 'content-type: application/json' \
     --data @"$HOME/.cache/audio-course/<course_id>.json"
   ```

   Never print the token or put it in any file.
3. On failure, show the error and tell the user the file path and that
   rerunning the same curl resubmits it (resubmits are safe: existing parts are
   kept, failed ones retried). A 400 names the problem: fix the JSON and resend.
   A resubmit must keep the same number of parts; a course with a different
   shape needs a new `course_id`.
   The response's `existing` lists parts that were already there and were left
   untouched. If you changed any of their scripts, say so: the old version is
   still what plays, and Hans can re-narrate it with the redo button on the
   admin page after editing, or you can resend under a new `course_id`.
4. On success, poll every 30 seconds until part 1 is `ready`, `error` or
   `skipped` (give up after 15 minutes and say so). For `error` or `skipped`,
   report the part's `error` text: `skipped` usually means a chapter URL had
   no readable text, so offer to resend that part as verbatim text instead:

   ```bash
   curl -sS "$URL/$TOKEN/api/course/<course_id>"
   ```

   Report part 1's status and length, and that the rest follow in order in the
   Learning feed. Do not wait for every part.
