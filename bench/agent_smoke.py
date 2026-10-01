#!/usr/bin/env python3
"""agent_smoke.py -- ask real agents to do the same GUI tasks and time them.

    python3 bench/agent_smoke.py --agent hermes --agent claude --runs 3
    python3 bench/agent_smoke.py --agent 'grok=grok -p {prompt}' --scenario calculator

Each scenario resets the app it uses, runs the agent's command with the prompt, and checks the answer against a
pattern. Output: one line per run, then a Markdown table of medians, and results/<timestamp>.jsonl next to this
file. It drives the real desktop: don't use the Mac while it runs.
"""
import argparse, json, os, re, shlex, statistics, subprocess, sys, time

AGENTS = {
    # {prompt} is replaced by the shell-quoted prompt.
    "hermes": "hermes -z {prompt}",
    "claude": "claude -p {prompt} --output-format json --allowedTools Bash",
    "grok": "grok -p {prompt}",
}


def chip():
    return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()


SCENARIOS = {
    "system-settings": {
        "reset": ["System Settings"],
        "prompt": "Open System Settings, go to General > About, and tell me this Mac's chip. Use the GUI, not a shell command.",
        "expect": lambda: re.escape(chip().replace("Apple ", "")),
    },
    "calculator": {
        "reset": ["Calculator"],
        "prompt": "Open Calculator, compute 56 x 123 in it, and tell me the result shown on its display.",
        "expect": lambda: r"6,?888",
    },
    "safari-wikipedia": {
        "reset": [],
        "prompt": "In Safari, open the English Wikipedia article on the Rosetta Stone, follow its link to Ptolemy V "
                  "Epiphanes, and tell me the birth date given on that page.",
        "expect": lambda: r"210",
    },
}


def run_once(name, template, scenario, timeout):
    for app in scenario["reset"]:
        subprocess.run(["pkill", "-x", app], capture_output=True)
    time.sleep(1.5)
    cmd = template.replace("{prompt}", shlex.quote(scenario["prompt"]))
    t0, p = time.time(), None
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=os.path.expanduser("~"))
        out, rc = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or "") if isinstance(e.stdout, str) else "", "timeout"
    secs = round(time.time() - t0, 1)
    turns = None
    try:  # claude --output-format json
        j = json.loads(p.stdout) if p else {}
        out, turns = j.get("result", out), j.get("num_turns")
    except Exception:
        pass
    ok = bool(re.search(scenario["expect"](), out or ""))
    return {"agent": name, "secs": secs, "ok": ok, "rc": rc, "turns": turns, "answer": (out or "").strip()[-200:]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", action="append", required=True,
                    help="name from %s, or name='command with {prompt}'" % ", ".join(AGENTS))
    ap.add_argument("--scenario", action="append", choices=list(SCENARIOS), help="default: all")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    agents = {}
    for a in args.agent:
        name, _, cmd = a.partition("=")
        agents[name] = cmd or AGENTS[name]
    scenarios = args.scenario or list(SCENARIOS)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    log = open(os.path.join(os.path.dirname(__file__), "results", f"{stamp}.jsonl"), "w")

    rows = {}
    for sc in scenarios:
        for name, template in agents.items():
            for i in range(args.runs):
                r = run_once(name, template, SCENARIOS[sc], args.timeout)
                r.update(scenario=sc, run=i + 1)
                log.write(json.dumps(r, ensure_ascii=False) + "\n"); log.flush()
                print(f"{sc:18} {name:8} run {i + 1}: {r['secs']:6.1f} s  {'PASS' if r['ok'] else 'FAIL'}"
                      f"{'' if r['turns'] is None else '  turns=%s' % r['turns']}  rc={r['rc']}", flush=True)
                rows.setdefault((sc, name), []).append(r)

    print("\n| Scenario | Agent | Runs | Passed | Median time |\n|---|---|---|---|---|")
    for (sc, name), rs in rows.items():
        times = [r["secs"] for r in rs if r["ok"]]
        med = f"{statistics.median(times):.1f} s" if times else "—"
        print(f"| {sc} | {name} | {len(rs)} | {sum(r['ok'] for r in rs)} | {med} |")
    print(f"\nraw results: bench/results/{stamp}.jsonl")


if __name__ == "__main__":
    sys.exit(main())
