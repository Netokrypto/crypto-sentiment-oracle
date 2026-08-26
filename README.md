# Crypto Sentiment Oracle

A GenLayer Intelligent Contract that turns any piece of text (a tweet,
headline, or Discord message) into a validator-consensus-verified
sentiment signal — `bullish` / `bearish` / `neutral` plus a confidence
level — for a given crypto asset ticker.

It's built as a trustless alternative to relying on a single off-chain
sentiment API: multiple validators independently run the classification
through an LLM, and only a result the Equivalence Principle agrees on
gets written on-chain. Signals aren't permanent the moment they're
written — anyone can dispute one, which triggers a fresh validator
re-vote that either upholds or overturns the original verdict.

## How it works

- `submit_signal(asset: str, text: str)` — sends the text to an LLM with
  a constrained prompt, keeps only the categorical `verdict` and
  `confidence` fields (dropping free-text reasoning, which wouldn't
  match byte-for-byte across different validator LLMs), and reaches
  consensus via `gl.eq_principle.strict_eq`. New signals start in
  `active` status.
- `dispute_signal(index: int, reason: str)` — challenges an `active`
  signal. The contract re-runs classification with the original text
  plus the dispute reason, and sets the signal's status to `upheld`
  (verdict unchanged) or `overturned` (verdict flipped by the re-vote).
  Only `active` signals can be disputed.
- `get_latest_signal(asset: str)` — returns the most recent signal for
  an asset, including its current status and dispute reason if any.
- `get_signal(index: int)` — returns a signal by its index in history.
- `get_signal_count()` — total number of signals recorded.

## Storage

- `signals: DynArray[Signal]` — full on-chain history.
- `latest_by_asset: TreeMap[str, u256]` — fast lookup of the latest
  signal index per asset.
- `Signal` is an `@allow_storage @dataclass` with `asset`, `verdict`,
  `confidence`, `submitter`, `text` (kept for re-adjudication),
  `status` (`active` / `upheld` / `overturned`), and `dispute_reason`.

## Example usage
