// Two addresses, and whether it can tell them apart.
//
//   node scripts/prove.mjs
//
// The difficulty is not finding a link. It is not finding one that is not
// there. A contract that answers KIN to every pair has answered nothing and is
// worse than useless, because it takes things away from people who did nothing.
//
// So three pairs are put to it on Base Sepolia:
//
//   two wallets where one funded the other, repeatedly    -> should be KIN
//   a wallet and a busy public contract                   -> should not be
//   a wallet and an address with no history at all        -> should be UNCERTAIN
//
// The third matters most. A register that answered UNRELATED to an unreadable
// history would be treating silence as a finding.
import { Wallet } from 'ethers';
import { createClient, createAccount } from 'genlayer-js';
import { testnetAsimov } from 'genlayer-js/chains';
import fs from 'fs';
import path from 'path';
import url from 'url';
import { KS, PASS } from './keys.mjs';

const ROOT = path.join(path.dirname(url.fileURLToPath(import.meta.url)), '..');
const out = [];
const say = line => { console.log(line); out.push(line); };

const caller = await Wallet.fromEncryptedJson(
  fs.readFileSync(`${KS}/padv.json`, 'utf8'), PASS.padv);
const asCaller = createClient({ chain: testnetAsimov, account: createAccount(caller.privateKey) });
const anybody = createClient({ chain: testnetAsimov });

const CHAIN = 'base-sepolia';
// A cutoff before any of today's work, so nothing this project did on Base
// afterwards can be what the answer rests on.
const BEFORE = '45200000';

const FUNDER = '0x80519c53f10D731e4FF83A7d9ACd69cF98da6258';
const FUNDED = '0x0b57877ec84D96b672CD47D8Ea4424283fDB9F6C';
const PUBLIC_CONTRACT = '0x4200000000000000000000000000000000000006';   // WETH
const EMPTY = '0x000000000000000000000000000000000000bEEF';

/** The testnet meters gas and sometimes reverts the consensus submission for
 *  reasons that have nothing to do with the call. Both say "not now". */
async function send(what, fn) {
  for (let attempt = 1; ; attempt++) {
    try { return await fn(); }
    catch (e) {
      const why = String(e?.details || e?.shortMessage || e?.message || e);
      const wait = Number(e?.cause?.data?.retryAfterMs || 0);
      const busy = /-32005|at capacity|rate limit|gas rate/i.test(why);
      const flaky = /reverted.*consensus contract|consensus contract.*reverted/i.test(why);
      if ((!busy && !flaky) || attempt >= 10) throw e;
      const pause = Math.max(wait, flaky ? 8000 : 1000) * attempt;
      say(`    (${what}: ${flaky ? 'the consensus submission reverted' : 'node at capacity'}, waiting ${Math.round(pause / 1000)}s)`);
      await new Promise(r => setTimeout(r, pause));
    }
  }
}

async function settle(hash, what) {
  const started = Date.now();
  await asCaller.waitForTransactionReceipt({
    hash, status: 'FINALIZED', retries: 220, interval: 12000 });
  say(`    (${what} settled in ${Math.round((Date.now() - started) / 1000)}s)`);
}

say('Are these two addresses the same hand?');
say('');
say('  judged on   GenLayer testnet Asimov');
say('  history from base-sepolia, before block ' + BEFORE);
say('');

const deployHash = await send('deploy', () => asCaller.deployContract({
  code: fs.readFileSync(path.join(ROOT, 'contracts', 'samehand.py')),
  args: [], leaderOnly: false }));
const deployed = await asCaller.waitForTransactionReceipt({
  hash: deployHash, status: 'FINALIZED', retries: 220, interval: 12000 });
const AT = deployed?.data?.contract_address ?? deployed?.recipient;
say('  contract ' + AT);
say('');

const read = (fn, args) => anybody.readContract({ address: AT, functionName: fn, args });

const pairs = [
  ['one funded the other, three times', FUNDER, FUNDED],
  ['a wallet and a public contract everybody uses', FUNDER, PUBLIC_CONTRACT],
  ['a wallet and an address with no history', FUNDER, EMPTY],
];

/** A round does not always answer, and when it does not, examine records
 *  nothing: an unanswered round is not evidence of anything. That is right and
 *  it is a trap for a script, because a pair nobody managed to examine looks
 *  exactly like a pair that came back with no link. So this watches the
 *  register rather than the call, and asks again until the contract has
 *  actually written something down. */
async function examineUntilRecorded(a, b) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    const hash = await send('examine', () => asCaller.writeContract({
      address: AT, functionName: 'examine',
      args: [a, b, CHAIN, BEFORE], value: 0n }));
    await settle(hash, `examine, attempt ${attempt}`);
    const f = JSON.parse(await read('finding', [a, b, CHAIN]));
    if (f.examined) return { found: f.finding, attempts: attempt };
    say('    the round produced no reading; asking again');
  }
  return { found: {}, attempts: 0 };
}

const results = {};
const rounds = {};
for (const [what, a, b] of pairs) {
  say(what);
  const { found, attempts } = await examineUntilRecorded(a, b);
  rounds[b.toLowerCase()] = attempts;
  say('    ' + found.reading + (found.grounds && found.grounds !== 'NONE'
    ? ' on ' + found.grounds + ' grounds' : ''));
  say('    ' + (found.why || '(no reason recorded)'));
  results[b.toLowerCase()] = found;
  if (attempts > 1) say('    (it took ' + attempts + ' rounds)');
  say('');
}

const funded = results[FUNDED.toLowerCase()] || {};
const publicOne = results[PUBLIC_CONTRACT.toLowerCase()] || {};
const empty = results[EMPTY.toLowerCase()] || {};

const size = JSON.parse(await read('size', []));
const boolFunded = await read('same_hand', [FUNDER, FUNDED, CHAIN]);
const boolPublic = await read('same_hand', [FUNDER, PUBLIC_CONTRACT, CHAIN]);
const boolNever = await read('same_hand', [FUNDED, PUBLIC_CONTRACT, CHAIN]);
const neverAsked = JSON.parse(await read('finding', [FUNDED, PUBLIC_CONTRACT, CHAIN]));
const reversed = JSON.parse(await read('finding', [FUNDED, FUNDER, CHAIN]));

say('  register: ' + size.examined + ' examined, ' + size.kin + ' kin');

const checks = [
  ['the pair where one funded the other is found', funded.reading === 'KIN'],
  ['and it says the evidence was direct', funded.grounds === 'DIRECT'],
  ['a public contract everybody uses is not kin', publicOne.reading !== 'KIN'],
  ['an address with no history is uncertain, not cleared',
    empty.reading === 'UNCERTAIN'],
  ['the boolean follows the finding',
    (boolFunded === true || boolFunded === 'true')
      && (boolPublic === false || boolPublic === 'false')],
  ['a pair nobody asked about reads false, like one found unrelated',
    boolNever === false || boolNever === 'false'],
  ['but the detail says nobody asked, which the boolean cannot',
    neverAsked.examined === false],
  ['asking in the other order finds the same answer',
    reversed.examined === true && reversed.finding.reading === funded.reading],
  ['every pair asked about was kept, not only the finding', size.examined === 3],
  ['and each was actually examined rather than quietly skipped',
    Object.values(rounds).every(n => n > 0)],
];

say('');
for (const [label, ok] of checks) say((ok ? '  ok   ' : ' FAIL  ') + label);
const failed = checks.filter(([, ok]) => !ok);
say('');
say(failed.length
  ? `${failed.length} of ${checks.length} checks failed`
  : `${checks.length} checks. It told them apart, which is the whole difficulty.`);

fs.mkdirSync(path.join(ROOT, 'results'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'results', 'proved.json'), JSON.stringify({
  proved_at: new Date().toISOString(),
  judged_on: 'genlayer testnet asimov', history_from: CHAIN,
  contract: AT, before_block: BEFORE,
  findings: results, rounds_needed: rounds, size,
  checks: checks.map(([label, ok]) => ({ label, ok })), transcript: out,
}, null, 2));
say('');
say('Written to results/proved.json');
process.exit(failed.length ? 1 : 0);
