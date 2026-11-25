#!/usr/bin/env python3
"""Phase 15c text patches of rpc-relay.

  patch-15c.py check <rpc-relay>
  patch-15c.py apply <rpc-relay> <outdir>

1. Two more lanes with their own daily Alchemy budget (relay.json alchemy_daily_cu):
   - fork:  the anvil forks (user farmfork). Alchemy first while the fork budget lasts, so proofs
            at a past block do not fall to public nodes once research is spent.
   - scout: the Qwen scouts (user earner). Public first, Alchemy as fallback, like research.
   The lane is chosen from the unix user of the connecting process (relay.json lane_by_user,
   e.g. {"farmfork": "fork", "earner": "scout"}), read from /proc/net/tcp once per connection,
   whatever lane the URL asks for. Nobody else may ask for fork or scout (they get research).
   The farmgate send socket (gate, signer) is not touched.
2. GET /health also returns this Alchemy billing cycle (CU so far, projection, share of the
   monthly allowance, alert above 85%) from ops.db, and lane_by_user.
3. GET /lane?lane=<x>: which unix user this connection is and which lane a request would use.
"""
import sys

PAIRS = [
    # 1. lanes + helpers ----------------------------------------------------------------------
    ('LANES = ("live", "paper", "research")\n',
     '''LANES = ("live", "paper", "research", "fork", "scout")     # fork, scout: 15c
MAPPED_ONLY = ("fork", "scout")     # given by relay.json lane_by_user, never by asking (15c)


def peer_user(client, server_port, paths=("/proc/net/tcp", "/proc/net/tcp6")):
    """Unix user name of the process at the other end of a loopback TCP connection, or None.
    The client's own socket row has local port = its port and remote port = ours (15c)."""
    import pwd
    try:
        cport = int(client[1])
    except (TypeError, ValueError, IndexError):
        return None
    for path in paths:
        try:
            with open(path, encoding="ascii", errors="replace") as f:
                next(f, None)
                for line in f:
                    p = line.split()
                    if len(p) < 8:
                        continue
                    try:
                        lport = int(p[1].rsplit(":", 1)[1], 16)
                        rport = int(p[2].rsplit(":", 1)[1], 16)
                    except (IndexError, ValueError):
                        continue
                    if lport == cport and rport == server_port:
                        try:
                            return pwd.getpwuid(int(p[7])).pw_name
                        except (KeyError, ValueError):
                            return None
        except OSError:
            continue
    return None


def mapped_lane(user, asked, lane_by_user):
    """The lane a request uses (15c): the user's lane from lane_by_user if it has one, else what it
    asked for - except fork and scout, which only lane_by_user hands out (else research)."""
    m = lane_by_user.get(user) if user else None
    if m in LANES:
        return m
    return "research" if asked in MAPPED_ONLY else asked


def cycle_from_db(db, allowance, cycle_day=1, now=None):
    """This Alchemy billing cycle as the relay counted it (rpc_stats), like farm-dash (15c)."""
    import sqlite3 as _sq
    now = now or dt.datetime.now(dt.timezone.utc)
    day = max(1, min(int(cycle_day), 28))
    y, m = now.year, now.month
    if now.day < day:
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
    start = dt.datetime(y, m, day, tzinfo=dt.timezone.utc)
    end = dt.datetime(ny, nm, day, tzinfo=dt.timezone.utc)
    try:
        con = _sq.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute("SELECT lane, sum(cu), min(day) FROM rpc_stats WHERE provider='alchemy' AND day>=? "
                               "GROUP BY 1", (start.strftime("%Y-%m-%d"),)).fetchall()
        finally:
            con.close()
    except _sq.Error as exc:
        return {"error": str(exc)}
    lanes = {r[0]: int(r[1] or 0) for r in rows}
    total = sum(lanes.values())
    since = start
    firsts = [r[2] for r in rows if r[2]]
    if firsts:
        try:
            since = max(start, dt.datetime.strptime(min(firsts), "%Y-%m-%d").replace(tzinfo=dt.timezone.utc))
        except ValueError:
            pass
    days = (now - since).total_seconds() / 86400
    proj = round(total + total / days * (end - now).total_seconds() / 86400) if total and days >= 0.5 else None
    share = round(proj / allowance, 3) if proj and allowance else None
    return {"since": since.strftime("%Y-%m-%d"), "ends": end.strftime("%Y-%m-%d"), "cu": total, "lanes": lanes,
            "allowance": allowance, "projected_cu": proj, "projected_share": share,
            "alert_85": bool(share and share > 0.85)}
'''),
    # Relay.__init__ ---------------------------------------------------------------------------
    ('        self.budget = config["alchemy_daily_cu"]        # lane -> cu/day\n',
     '''        self.budget = config["alchemy_daily_cu"]        # lane -> cu/day
        self.lane_by_user = config.get("lane_by_user") or {}                  # unix user -> lane (15c)
        self.monthly_cu = int(config.get("alchemy_monthly_cu", 95_200_000))   # 15c
        self.cycle_day = int(config.get("alchemy_cycle_day", 1))
        self._cycle = None
'''),
    # providers: the fork lane ----------------------------------------------------------------
    ('''        if lane == "live":
            return alchemy + public
''',
     '''        if lane == "live":
            return alchemy + public
        if lane == "fork" and alchemy and spent < self.budget.get(lane, 0):
            # 15c: fork state for proofs: Alchemy first while the fork lane's own budget lasts
            return alchemy + public
'''),
    # Relay.cycle, before call() ---------------------------------------------------------------
    ('''    def call(self, chain, lane, method, params, req_id, allow_send=False''',
     '''    def cycle(self):
        """cycle_from_db, cached for 2 minutes (15c)."""
        if self._cycle and time.monotonic() - self._cycle[0] < 120:
            return self._cycle[1]
        v = cycle_from_db(DB_PATH, self.monthly_cu, self.cycle_day)
        self._cycle = (time.monotonic(), v)
        return v

    def call(self, chain, lane, method, params, req_id, allow_send=False'''),
    # Handler: /health, /lane, peer lane ------------------------------------------------------
    ('''        if self.path == "/health":
            day = utc_day()
            spend = {lane: self.relay.stats.alchemy_cu_today(lane) for lane in LANES}
            self.send_json(200, {"ok": True, "day": day, "alchemy_cu_today": spend,
                                 "budget": self.relay.budget, "chains": sorted(self.relay.chains)})
        else:
''',
     '''        if self.path == "/health":
            day = utc_day()
            spend = {lane: self.relay.stats.alchemy_cu_today(lane) for lane in LANES}
            self.send_json(200, {"ok": True, "day": day, "alchemy_cu_today": spend,
                                 "budget": self.relay.budget, "chains": sorted(self.relay.chains),
                                 "cycle": self.relay.cycle(), "lane_by_user": self.relay.lane_by_user})
        elif self.path.startswith("/lane"):
            asked = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("lane", ["research"])[0]
            self.send_json(200, {"user": self.peer(), "asked": asked, "lane": self.peer_lane(asked)})
        else:
'''),
    ('''    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
''',
     '''    def peer(self):
        """Unix user of this connection, looked up once per connection (15c)."""
        if not hasattr(self, "_peer_user"):
            ca = self.client_address
            self._peer_user = (peer_user(ca, self.server.server_address[1])
                               if isinstance(ca, tuple) and ca and ca[0] != "unix" else None)
        return self._peer_user

    def peer_lane(self, asked):
        if self.allow_send:                           # the farmgate send socket: unchanged
            return asked
        return mapped_lane(self.peer(), asked, self.relay.lane_by_user)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
'''),
    ('        lane = urllib.parse.parse_qs(parsed.query).get("lane", ["research"])[0]\n',
     '        lane = urllib.parse.parse_qs(parsed.query).get("lane", ["research"])[0]\n'
     '        lane = self.peer_lane(lane)                  # the unix user decides fork / scout (15c)\n'),
]


def patched(path, check_only=False):
    text = open(path, encoding="utf-8").read()
    for i, (old, new) in enumerate(PAIRS, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{path}: patch {i} matches {n} times (expected 1); nothing was changed")
        if not check_only:
            text = text.replace(old, new)
    return text


def main():
    a = sys.argv
    if len(a) == 3 and a[1] == "check":
        patched(a[2], True)
        return print(f"  rpc-relay: {len(PAIRS)} patches match")
    if len(a) == 4 and a[1] == "apply":
        with open(f"{a[3]}/rpc-relay", "w", encoding="utf-8") as f:
            f.write(patched(a[2]))
        return print(f"  patched copy written to {a[3]}")
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
