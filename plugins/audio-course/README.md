# audio-course

Ask for an audio course on any topic, or an audiobook of a free public book, and
it lands in your self-hosted podcastfeeds "Learning" feed.

The session asks why you want to learn it and what you already know, researches
the topic, and shows an outline for approval. Only then does it write one
listening-friendly script per part and send them to podcastfeeds, which
narrates them in order. Code and links go in the show notes.

Requires a running podcastfeeds instance with `/api/course` and these
environment variables: `PODCASTFEEDS_URL`, and `PODCASTFEEDS_TOKEN` or
`PODCASTFEEDS_TOKEN_FILE`.
