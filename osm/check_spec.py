"""Does osm/spec.json still ask for the same kinds and tags as Tobler's catalogue/osm-snapshot.json?

Tobler owns the kinds and tags (its reader and its Overpass fallback use them); the atlas owns the markets and the
build. The copy here is what gets built, so a change on Tobler's side is a request, not a silent rebuild: this stops
the build with the difference, and the old release stays live until osm/spec.json is updated to match.

    python3 osm/check_spec.py                      # fetch Tobler's file from GitHub (main)
    python3 osm/check_spec.py --tobler path.json   # or compare with a local copy
"""
import argparse, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOBLER_URL = "https://raw.githubusercontent.com/pushpingeo/tobler/main/catalogue/osm-snapshot.json"
SHARED = ("version", "groups", "keep_tags", "kinds")  # Tobler's part; "markets" and "about" are left out


def differences(ours, theirs):
    out = []
    for k in SHARED:
        if k == "kinds":
            a, b = ours.get(k, {}), theirs.get(k, {})
            for name in sorted(set(a) | set(b)):
                if name not in a: out.append(f"kind '{name}' is new in Tobler's file")
                elif name not in b: out.append(f"kind '{name}' is no longer in Tobler's file")
                elif a[name] != b[name]: out.append(f"kind '{name}' differs: ours {json.dumps(a[name])}, Tobler's {json.dumps(b[name])}")
        elif ours.get(k) != theirs.get(k):
            out.append(f"{k} differs: ours {json.dumps(ours.get(k))}, Tobler's {json.dumps(theirs.get(k))}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tobler", help="local copy of Tobler's catalogue/osm-snapshot.json (default: fetch main)")
    a = ap.parse_args(argv)
    ours = json.load(open(os.path.join(HERE, "spec.json")))
    if a.tobler:
        theirs = json.load(open(a.tobler))
    else:
        with urllib.request.urlopen(TOBLER_URL, timeout=30) as r:
            theirs = json.load(r)
    diff = differences(ours, theirs)
    if diff:
        print("osm/spec.json no longer matches Tobler's catalogue/osm-snapshot.json:")
        for d in diff: print("  -", d)
        print("Copy Tobler's kinds, groups, keep_tags and version into osm/spec.json (keep our markets), then rerun.")
        return 1
    print(f"osm/spec.json matches Tobler's kinds and tags (spec version {ours['version']}, {len(ours['kinds'])} kinds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
