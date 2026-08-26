# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass

VALID_VERDICTS = ("bullish", "bearish", "neutral")
VALID_CONFIDENCE = ("low", "medium", "high")
VALID_STATUS = ("active", "disputed", "upheld", "overturned")


@allow_storage
@dataclass
class Signal:
    asset: str
    verdict: str
    confidence: str
    submitter: Address
    text: str
    status: str
    dispute_reason: str


class CryptoSentimentOracle(gl.Contract):
    signals: DynArray[Signal]
    latest_by_asset: TreeMap[str, u256]
    signal_count: u256

    def __init__(self):
        self.signal_count = u256(0)

    def _classify(self, asset_key: str, text: str) -> dict:
        prompt = f"""
You are a neutral crypto market analyst. Classify the sentiment of the
following text specifically toward the asset "{asset_key}".

Text:
\"\"\"{text}\"\"\"

Respond using ONLY the following JSON format, nothing else:
{{
"verdict": "bullish" | "bearish" | "neutral",
"confidence": "low" | "medium" | "high"
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters, your output
must be pure JSON without any formatting prefix or suffix. This result
should be perfectly parseable by a JSON parser without errors.
"""

        def nondet():
            res = gl.nondet.exec_prompt(prompt)
            backticks = "``" + "`"
            res = res.replace(backticks + "json", "").replace(backticks, "")
            data = json.loads(res)
            verdict = str(data["verdict"]).strip().lower()
            confidence = str(data["confidence"]).strip().lower()
            if verdict not in VALID_VERDICTS:
                verdict = "neutral"
            if confidence not in VALID_CONFIDENCE:
                confidence = "low"
            return json.dumps({"verdict": verdict, "confidence": confidence})

        result_raw = gl.eq_principle.strict_eq(nondet)
        return json.loads(result_raw)

    @gl.public.write
    def submit_signal(self, asset: str, text: str) -> None:
        asset_key = asset.strip().upper()
        if len(asset_key) == 0:
            raise Exception("asset ticker cannot be empty")
        if len(text.strip()) == 0:
            raise Exception("text cannot be empty")

        result = self._classify(asset_key, text)

        signal = Signal(
            asset=asset_key,
            verdict=result["verdict"],
            confidence=result["confidence"],
            submitter=gl.message.sender_address,
            text=text,
            status="active",
            dispute_reason="",
        )
        self.signals.append(signal)
        self.latest_by_asset[asset_key] = self.signal_count
        self.signal_count += u256(1)

    @gl.public.write
    def dispute_signal(self, index: int, reason: str) -> None:
        if index < 0 or index >= int(self.signal_count):
            raise Exception("index out of range")
        if len(reason.strip()) == 0:
            raise Exception("dispute reason cannot be empty")

        s = self.signals[index]
        if s.status != "active":
            raise Exception("only an active signal can be disputed")

        combined_text = (
            f"{s.text}\n\n"
            f"A reviewer challenges the original classification and argues:\n"
            f"{reason}\n\n"
            f"Re-evaluate the sentiment considering both the original text "
            f"and the challenge above."
        )
        result = self._classify(s.asset, combined_text)

        new_signal = Signal(
            asset=s.asset,
            verdict=s.verdict,
            confidence=s.confidence,
            submitter=s.submitter,
            text=s.text,
            status="overturned" if result["verdict"] != s.verdict else "upheld",
            dispute_reason=reason,
        )
        if result["verdict"] != s.verdict:
            new_signal.verdict = result["verdict"]
            new_signal.confidence = result["confidence"]
        self.signals[index] = new_signal

    @gl.public.view
    def get_latest_signal(self, asset: str) -> TreeMap[str, typing.Any]:
        asset_key = asset.strip().upper()
        idx = self.latest_by_asset.get(asset_key, None)
        if idx is None:
            return {"asset": asset_key, "verdict": "none", "confidence": "none", "status": "none"}
        return self._to_dict(self.signals[int(idx)])

    @gl.public.view
    def get_signal(self, index: int) -> TreeMap[str, typing.Any]:
        if index < 0 or index >= int(self.signal_count):
            raise Exception("index out of range")
        return self._to_dict(self.signals[index])

    @gl.public.view
    def get_signal_count(self) -> int:
        return int(self.signal_count)

    def _to_dict(self, s: Signal) -> dict:
        return {
            "asset": s.asset,
            "verdict": s.verdict,
            "confidence": s.confidence,
            "status": s.status,
            "dispute_reason": s.dispute_reason,
}
