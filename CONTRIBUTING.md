# Contributing

Thanks for your interest! The project is in its architecture phase, so the most useful contributions right now are ideas and feedback in issues and discussions.

## How changes get in

`main` is protected. Nobody pushes to it directly, maintainers included.

1. **Big changes start as an issue or discussion**, so we agree on the approach before anyone writes code.
2. **Work on a branch** named `<your-github-name>/<topic>`, for example `twadi/hybrid-retrieval`.
3. **Open a pull request** using the template. Keep it focused on one change.
4. **Get one approving review** from another maintainer, with all conversations resolved and CI green.
5. **Squash and merge.** The branch is deleted automatically.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add reciprocal rank fusion to hybrid retrieval
fix: keep citations when the answer spans two chunks
docs: ADR for the vector store choice
```

Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `ci`, `chore`.

## Quality bar

- **Tests** come with every behavior change.
- **Evaluation numbers** come with every change to retrieval or generation: before and after, on the same dataset.
- **Architectural decisions** get a short decision record in `docs/adr/`.

Development setup instructions will be added once the architecture is settled.
