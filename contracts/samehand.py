# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Are these two addresses the same hand?

Every airdrop, vote, allowlist and grant round has the same hole in it. One
person opens forty wallets and takes forty shares, and the chain cannot tell,
because to a chain forty addresses are forty addresses. The usual answers are a
minimum balance, a wallet age, a captcha: each of them costs the honest person
something and costs the determined one an afternoon.

The reason no contract solves it is that it is not a computation. Two wallets
funded by the same exchange are not related, and a thousand people share that
exchange. Two wallets funded by the same fresh address, minutes apart, for the
same amount, that had never held anything before and did nothing else, are one
person. The difference is a judgement about a pattern, and the pattern is in
another chain's history.

So this reads that history and asks a round of validators one question.

## What it answers

    same_hand(case) -> bool

One boolean, for another contract to act on. Nothing here distributes anything,
blocks anybody or holds money. It says what it found and the caller decides what
that is worth.

## What it refuses

**It never answers from silence.** A history that could not be read is
UNCERTAIN, which is not a finding. Treating an unreadable history as guilt would
punish anybody whose funding is hard to fetch, which is not the same set of
people as those who are cheating.

**It never widens on its own.** A finding is about the two addresses in the
question and no others. If A is the same hand as B, and B as C, this does not
conclude anything about A and C: the caller can ask, and until somebody does,
nothing has been decided about them.

**It says how sure it was.** A round that found a direct transfer between the
two and a round that found a coincidence of timing are both KIN, and a caller
that cannot tell them apart will treat a guess like a proof.

## Where it stops, plainly

It reads transaction lists, which do not include internal transfers. Money sent
by a contract, which is how most faucets and many exchanges pay, is invisible
here. So is a person who funds their wallets from separate exchange withdrawals
months apart. This raises the cost of hiding. It does not
end it, and a caller that treats UNRELATED as proof of innocence has
misunderstood what it bought.
"""

from genlayer import *
import json
import typing


KIN = "KIN"
UNRELATED = "UNRELATED"
UNCERTAIN = "UNCERTAIN"
READINGS = (KIN, UNRELATED, UNCERTAIN)

# How much the round was leaning on. A finding drawn from a direct transfer
# between the two is not the same kind of fact as one drawn from two wallets
# happening to be funded the same afternoon, and a caller that cannot tell them
# apart will spend a guess as though it were a proof.
DIRECT = "DIRECT"          # one paid the other
SHARED = "SHARED"          # both funded by the same address, in a way that means something
CIRCUMSTANTIAL = "CIRCUMSTANTIAL"   # timing and amounts only
NONE = "NONE"
GROUNDS = (DIRECT, SHARED, CIRCUMSTANTIAL, NONE)

MAX_HISTORY = 1500
MAX_WHY = 300
MAX_TRANSFERS = 15

# Explorers that answer without a key. The alternative is an API key written
# into a public contract, which is a key published: anybody can read it, and
# changing it means redeploying everything that depended on it.
EXPLORERS = {
    "ethereum": "https://eth.blockscout.com",
    "base": "https://base.blockscout.com",
    "base-sepolia": "https://base-sepolia.blockscout.com",
    "optimism": "https://optimism.blockscout.com",
    "gnosis": "https://gnosis.blockscout.com",
}


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _addr(value) -> str:
    text = str(value).strip().lower()
    if not text.startswith("0x") or len(text) != 42:
        return ""
    for character in text[2:]:
        if character not in "0123456789abcdef":
            return ""
    return text


def _clip(text: str, limit: int) -> str:
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit] + " [...]"


def _whole(value) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return -1


def _field(raw: str, name: str, allowed, fallback: str) -> str:
    try:
        text = str(raw).strip()
        obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
        if isinstance(obj, dict):
            said = str(obj.get(name, "")).strip().upper()
            return said if said in allowed else fallback
    except Exception:
        pass
    return fallback


def _why(raw: str) -> str:
    try:
        text = str(raw).strip()
        obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
        if isinstance(obj, dict):
            return _clip(str(obj.get("why", "")), MAX_WHY)
    except Exception:
        pass
    return ""


def _incoming(body: str, mine: str, before_block: int) -> str:
    """Money that came in, reduced to who sent it, how much, and when.

    Three things happen here and all three matter.

    The explorer answers with a great deal per transaction and almost none of it
    bears on the question. Handing a round four thousand characters of gas
    prices and nonces is asking it to find the question inside the answer.

    The cutoff is applied by the explorer and checked again here, rather than
    asked for in the prompt. The first version of this asked the round to
    disregard anything after the cutoff and the round did not: it found a
    transfer between the two addresses, said in its own reasoning that it came
    after the date it had been told to ignore, and used it anyway. A limit that
    matters is a limit the model never sees past.

    And only what came *in* is kept. The endpoint returns everything the address
    touched, most of it outgoing, and an address's own spending says nothing
    about who funded it.
    """
    try:
        payload = json.loads(body)
    except Exception:
        return ""
    rows = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return ""

    lines = []
    for item in rows:
        if len(lines) >= MAX_TRANSFERS:
            break
        if not isinstance(item, dict):
            continue
        if str(item.get("to", "")).lower() != mine:
            continue
        block = _whole(item.get("blockNumber"))
        if before_block > 0 and (block < 0 or block >= before_block):
            continue
        value = str(item.get("value", "0"))
        if value in ("", "0"):
            continue
        lines.append(json.dumps({
            "from": str(item.get("from", "")).lower(),
            "value": value,
            "block": block,
        }))
    return chr(10).join(lines)


def _task(one: str, two: str, before_block: str,
          one_history: str, two_history: str) -> str:
    """Built from locals only. Nothing here may touch `self`."""
    cutoff = (f"Everything below happened before block {before_block}. "
              "Nothing after it was fetched, so there is nothing later to weigh.")
    return f"""Two addresses. One question: is the same person behind both?

FIRST ADDRESS: {one}
SECOND ADDRESS: {two}

{cutoff}

MONEY THAT CAME INTO THE FIRST, one transfer per line:
{one_history}

MONEY THAT CAME INTO THE SECOND:
{two_history}

Answer {KIN} only if the histories show one hand. That looks like: one of these
addresses funded the other; or both were funded by the same address that funds
few others, close together in time; or both were funded once, for amounts that
match, shortly before they were needed, having held nothing before.

Answer {UNRELATED} if the link is not there. Two wallets funded by the same
exchange, bridge or faucet are not related: those pay thousands of people and a
shared one is evidence of nothing. A wallet with its own long and varied history
is somebody living their own life.

Answer {UNCERTAIN} if what is here is too thin to carry either answer. Silence
is not guilt: somebody whose funding is hard to read has not thereby done
anything.

One side may say nothing readable came in. That is common and it is not
suspicious on its own: an address topped up by a faucet or an exchange through a
contract shows no incoming transfer in a list like this. If the other side shows
a transfer from this one, that is still a direct link and still {KIN}. If
neither side shows anything, that is {UNCERTAIN}.

Then say what you were leaning on, in the field named grounds:
  {DIRECT} if one of them paid the other
  {SHARED} if a third address funded both and that address is not an exchange,
    bridge, faucet or other payer of crowds
  {CIRCUMSTANTIAL} if it rests on timing and amounts alone
  {NONE} if the answer is not {KIN}

Be sparing with {KIN}. This will be used to take something away from whoever it
names, and a false {KIN} takes it from somebody who did nothing wrong. Where the
evidence is only that two wallets appeared around the same time, say
{CIRCUMSTANTIAL} and let whoever asked decide what that is worth.

Reply with bare JSON and nothing else:
{{"reading": "{KIN}" or "{UNRELATED}" or "{UNCERTAIN}",
  "grounds": "{DIRECT}" or "{SHARED}" or "{CIRCUMSTANTIAL}" or "{NONE}",
  "why": "one sentence naming what decided it"}}"""


class SameHand(gl.Contract):
    """Findings about pairs of addresses, and nothing else."""

    # "chain|first|second" -> the finding, as JSON. Flat rather than nested,
    # because a storage collection cannot be created in user code: assigning a
    # fresh DynArray into a TreeMap raises "this class can't be instantiated by
    # user", and that exception never leaves the round. What a caller sees is
    # only that no reading came back.
    found: TreeMap[str, str]
    # Append only, including the pairs that came back UNRELATED. A register
    # holding only its findings cannot be told apart from a net.
    asked: DynArray[str]

    def __init__(self) -> None:
        pass

    @staticmethod
    def _key(chain: str, one: str, two: str) -> str:
        # The pair is unordered: asking about A and B is asking about B and A,
        # and a register that answered differently depending on the order would
        # be two registers wearing one name.
        first, second = (one, two) if one < two else (two, one)
        return chain + "|" + first + "|" + second

    @gl.public.write
    def examine(self, first: str, second: str, chain: str, before_block: str) -> str:
        """Ask whether two addresses are one person, as of a block.

        Open to anybody. A register only its owner could write to would be a
        register whose owner decides who counts as a sybil, which is the thing
        this exists to avoid having to trust.
        """
        one = _addr(first)
        two = _addr(second)
        where = str(chain).strip().lower()
        cutoff = _whole(before_block)

        if not one or not two:
            return json.dumps({"ok": False, "error": "give two real addresses"})
        if one == two:
            return json.dumps({"ok": False,
                               "error": "an address is already itself"})
        if where not in EXPLORERS:
            return json.dumps({"ok": False,
                               "error": "no keyless explorer known for that chain"})
        if cutoff < 0:
            return json.dumps({"ok": False,
                               "error": "give a block to look before, or 0 for all"})

        key = SameHand._key(where, one, two)
        if key in self.found:
            return json.dumps({"ok": False, "error": "already examined",
                               "finding": json.loads(self.found[key])})

        # The window is asked for rather than filtered afterwards. Blockscout's
        # newest-first listing returns one page, and for an address busy since
        # the cutoff that page is entirely on the wrong side of it: the filter
        # then removes everything and the answer becomes that no history exists,
        # which is the opposite of true.
        base = EXPLORERS[where]
        end_block = str(cutoff) if cutoff > 0 else "99999999"
        one_url = (base + "/api?module=account&action=txlist&address=" + one
                   + "&startblock=0&endblock=" + end_block
                   + "&sort=asc&page=1&offset=40")
        two_url = (base + "/api?module=account&action=txlist&address=" + two
                   + "&startblock=0&endblock=" + end_block
                   + "&sort=asc&page=1&offset=40")

        def look() -> str:
            # Locals only. Nothing here reads self and nothing here raises:
            # either would end the transaction rather than the round.
            #
            # Flat, with the two fetches written out. A nested definition inside
            # this block is the difference between a round that answers and one
            # that returns nothing at all, and a round that returns nothing does
            # not say why.
            one_history = ""
            two_history = ""
            try:
                answer = gl.nondet.web.get(one_url)
                body = getattr(answer, "body", b"")
                if isinstance(body, (bytes, bytearray)):
                    body = body.decode("utf-8", "replace")
                one_history = _clip(_incoming(str(body), one, cutoff), MAX_HISTORY)
            except Exception:
                one_history = ""
            try:
                answer = gl.nondet.web.get(two_url)
                body = getattr(answer, "body", b"")
                if isinstance(body, (bytes, bytearray)):
                    body = body.decode("utf-8", "replace")
                two_history = _clip(_incoming(str(body), two, cutoff), MAX_HISTORY)
            except Exception:
                two_history = ""

            # One is enough. Requiring both was wrong, and wrong in the case
            # this exists for: when A funded B, the whole answer is in B's
            # incoming history, and A's own is beside the point. The funder in
            # a cluster is usually the side with nothing readable, because it
            # was topped up by a faucet or an exchange through a contract, and
            # an internal transfer does not appear in a transaction list at all.
            if not one_history and not two_history:
                return json.dumps({
                    "reading": UNCERTAIN, "grounds": NONE,
                    "why": "neither history could be read",
                })
            if not one_history:
                one_history = "(nothing readable came into this address in the window)"
            if not two_history:
                two_history = "(nothing readable came into this address in the window)"
            try:
                return str(gl.nondet.exec_prompt(
                    _task(one, two, str(cutoff), one_history, two_history)))
            except Exception as e:
                # Not swallowed. An empty return here arrives at the caller as
                # "no reading", which is equally true of a fetch that failed and
                # a prompt that was refused, and those want different fixes.
                return json.dumps({
                    "reading": UNCERTAIN, "grounds": NONE,
                    "why": _clip("the prompt failed: " + str(e), MAX_WHY),
                })

        raw = gl.eq_principle.prompt_comparative(
            look,
            principle=(
                f"Both answers must carry the same value in the field named reading, one of "
                f"{KIN}, {UNRELATED} or {UNCERTAIN}. That single field decides whether "
                "somebody is treated as a duplicate of somebody else, so two readers "
                "differing on it are not wording a judgement differently, they are "
                "disagreeing about whether these are one person. The grounds and the "
                "sentence are not compared, and the two readers will not have fetched "
                "identical copies of the histories."
            ),
        )

        reading = _field(raw, "reading", READINGS, "")
        if not reading:
            return json.dumps({"ok": False,
                               "error": "the round produced no reading this "
                                        "contract recognises",
                               "round_said": _clip(str(raw), 400)})

        finding = {
            "chain": where,
            "first": one,
            "second": two,
            "before_block": cutoff,
            "reading": reading,
            "grounds": _field(raw, "grounds", GROUNDS, NONE) if reading == KIN else NONE,
            "why": _why(raw),
            "at": _now_iso(),
        }
        self.found[key] = json.dumps(finding)
        self.asked.append(key)
        return json.dumps({"ok": True, **finding})

    # ------------------------------------------------------------------ reads

    @gl.public.view
    def same_hand(self, first: str, second: str, chain: str) -> bool:
        """The whole integration surface, and the only thing worth calling.

        False for a pair nobody has examined, which is the same answer it gives
        for a pair examined and found unrelated. That is deliberate: a caller
        should not be able to tell "we looked and found nothing" from "nobody
        looked" through this call, because acting differently on the two would
        mean acting on an absence of evidence.
        """
        one = _addr(first)
        two = _addr(second)
        where = str(chain).strip().lower()
        if not one or not two:
            return False
        key = SameHand._key(where, one, two)
        if key not in self.found:
            return False
        return json.loads(self.found[key])["reading"] == KIN

    @gl.public.view
    def finding(self, first: str, second: str, chain: str) -> str:
        """Everything about a pair, for anybody who wants more than the boolean.

        This is where "we looked and found nothing" and "nobody looked" are told
        apart, because a person deciding whether to trust the answer needs the
        difference that a calling contract should not act on.
        """
        one = _addr(first)
        two = _addr(second)
        where = str(chain).strip().lower()
        key = SameHand._key(where, one, two)
        if key not in self.found:
            return json.dumps({"examined": False,
                               "note": "nobody has asked about this pair"})
        return json.dumps({"examined": True,
                           "finding": json.loads(self.found[key])})

    @gl.public.view
    def size(self) -> str:
        kin = 0
        for position in range(len(self.asked)):
            entry = json.loads(self.found[self.asked[position]])
            if entry["reading"] == KIN:
                kin += 1
        return json.dumps({
            "examined": len(self.asked),
            "kin": kin,
            "note": ("every pair asked about is kept, including the ones found "
                     "unrelated; a register holding only its findings could not "
                     "be told apart from a net"),
        })

    @gl.public.view
    def asked_at(self, index: str) -> str:
        position = _whole(index)
        if position < 0 or position >= len(self.asked):
            return json.dumps({"ok": False, "error": "no examination at that index"})
        return json.dumps({"ok": True,
                           "finding": json.loads(self.found[self.asked[position]])})
