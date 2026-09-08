# Same Hand

**Are these two addresses the same person?**

Every airdrop, vote, allowlist and grant round has the same hole in it. One
person opens forty wallets and takes forty shares, and the chain cannot tell,
because to a chain forty addresses are forty addresses.

The usual answers all cost the honest person something and cost the determined
one an afternoon: a minimum balance, a wallet age, a captcha, a social account.

## Why no contract solves this

Because it is not a computation.

> Two wallets funded by the same exchange are strangers. A thousand people share
> that exchange.
>
> Two wallets funded by the same fresh address, minutes apart, for matching
> amounts, that had held nothing before and did nothing else, are one person.

The difference between those two sentences is a judgement about a pattern, and
the pattern is in another chain's transaction history. A contract can fetch the
history. It cannot read it.

## The whole surface

```
same_hand(first, second, chain) -> bool
```

One boolean, for another contract to act on. Nothing here distributes anything,
blocks anybody, or holds money. It says what it found and the caller decides
what that is worth.

`finding(first, second, chain)` returns the rest: the reading, what the round
was leaning on, its reason in its own words, and the block it looked before.

## Proved on chain

Judged on GenLayer testnet Asimov at
[`0xEfF7b5d8F05501C351712C1B30108967bC79950C`](https://explorer-asimov.genlayer.com/address/0xEfF7b5d8F05501C351712C1B30108967bC79950C),
reading Base Sepolia history through Blockscout, looking only before block
45,200,000.

The difficulty is not finding a link. It is not finding one that is not there,
so two of the three pairs had to come back negative.

**A wallet that really was funded by the other, three times.**

> `KIN` on `DIRECT` grounds — *"The first address sent three transfers to the
> second address, including two large similar amounts and one smaller amount,
> establishing a direct funding relationship."*

**A wallet against a contract everybody uses.**

> `UNRELATED` — *"First address shows no incoming transfers; second address has
> multiple diverse funders including bridges/exchanges and large varied amounts
> with no connection to first address."*

**A wallet against an address with no history at all.**

> `UNCERTAIN` — *"neither history could be read"*

That last one is the one that matters. A register answering `UNRELATED` to
silence would be treating an absence of evidence as a finding, and this is used
to take something away from whoever it names.

Ten checks, in [`results/proved.json`](results/proved.json), including that the
boolean follows the finding, that asking in the other order gives the same
answer, and that a pair nobody has examined reads the same as one examined and
cleared.

```bash
npm install
node scripts/prove.mjs
```

## What it refuses to do

**It never answers from silence.** A history that could not be read is
`UNCERTAIN`, which is not a finding. Treating an unreadable history as guilt
punishes people whose funding is hard to fetch, and that is not the same set of
people as those who are cheating.

**It never widens on its own.** A finding is about the two addresses in the
question. If A is the same hand as B, and B as C, nothing has been decided about
A and C until somebody asks.

**It says how sure it was.** A round that found a direct transfer and a round
that found a coincidence of timing both say `KIN`. `DIRECT`, `SHARED` and
`CIRCUMSTANTIAL` are there so a caller cannot spend a guess as though it were a
proof.

**Anybody can write to it.** A register only its owner could add to would be a
register whose owner decides who counts as a sybil, which is the thing this
exists to avoid having to trust.

## Where it stops

**It reads transaction lists, which do not include internal transfers.** Money
sent by a contract, which is how most faucets and many exchanges pay, is
invisible here.

**A person who funds their wallets from separate exchange withdrawals months
apart leaves nothing to find.** This raises the cost of hiding. It does not end
it, and a caller who treats `UNRELATED` as proof of innocence has misunderstood
what they bought.

**One round is not a verdict for all time.** Rounds sometimes produce no answer
at all; the proof records how many were needed per pair, and one of the three
took two.

## Four things that went wrong first

Each of them taught the contract something, and each is a comment in the source
rather than a lesson someone has to learn again.

**Filtering after fetching.** Blockscout returns a newest-first page. For an
address busy since the cutoff, that whole page is on the wrong side of it, the
filter removes everything, and the answer becomes that no history exists, which
is the opposite of true. The window is asked of the explorer now.

**Requiring both histories.** That broke exactly the case this exists for: when
A funded B, the answer is entirely in B's incoming history, and the funder in a
cluster is usually the side with nothing readable, because it was topped up
through a contract.

**Asking the prompt to respect the cutoff.** It did not. It found a transfer
between the two, said in its own reasoning that it came after the date it had
been told to disregard, and used it anyway. The cutoff is applied in code now,
where the model cannot see past it.

**Reading an unanswered round as a finding.** A pair nobody managed to examine
looked exactly like a pair with no link. The proof watches the register rather
than the call.

## Notes for the next person on GenLayer

Two of these cost hours and neither is in any documentation.

**A storage collection cannot be created in user code.** Assigning a fresh
`DynArray` into a `TreeMap` raises *"this class can't be instantiated by user"*,
and that exception never leaves the round. What the caller sees is only that no
reading came back, which is equally true of a fetch that failed and a prompt
that was refused.

**The testnet receipt has no `leader_receipt`.** The answer is hex inside
`eqBlocksOutputs`. The debugging path that works on Studionet returns nothing on
testnet, which reads as though nothing happened.

## Licence

AGPL-3.0-or-later. See [LICENSE](LICENSE).
