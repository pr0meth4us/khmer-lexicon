"""Aho-Corasick multi-pattern matching.

One pass over the text finds every pattern in the set, instead of one full
pass per pattern. Build cost is O(sum of pattern lengths); search cost is
O(len(text)) regardless of how many patterns there are.

Pure Python, no dependencies. Worth it above ~220 patterns: below that, the
naive `p in text` loop wins because str.__contains__ is C and this walk is not.
See bench_scan.py in egd-platform for the measurement.

apps/doc-pipeline in egd-platform carries its own copy of this file rather than
depending on this package -- that repo has no requirements plumbing, and one
vendored module was judged cheaper than introducing some.

    ac = AhoCorasick(["ai tools", "prompt", "chatbot"])
    ac.matched("we used ai tools and a chatbot")   -> {"ai tools", "chatbot"}
"""
from collections import deque


class AhoCorasick:
    """A trie of the patterns, plus failure links.

    `goto[node]` maps a character to the next node -- that is exactly the
    trie from the lessons. `fail[node]` points at the longest proper suffix
    of the current match that is also a prefix of some pattern, which is what
    lets the search continue without ever rewinding the text pointer.
    """

    __slots__ = ("goto", "fail", "out", "_empty")

    def __init__(self, patterns):
        patterns = [p for p in patterns if p]
        self._empty = not patterns
        self.goto = [{}]                 # goto[node][char] -> node
        self.fail = [0]
        self.out = [frozenset()]
        out = [set()]

        for pattern in patterns:         # build the trie: reuse or create
            node = 0
            for ch in pattern:
                nxt = self.goto[node].get(ch)
                if nxt is None:
                    self.goto.append({})
                    self.fail.append(0)
                    out.append(set())
                    nxt = len(self.goto) - 1
                    self.goto[node][ch] = nxt
                node = nxt
            out[node].add(pattern)

        # failure links, breadth-first so a node's fail target is already done
        queue = deque()
        for child in self.goto[0].values():
            self.fail[child] = 0
            queue.append(child)
        while queue:
            node = queue.popleft()
            for ch, child in self.goto[node].items():
                state = self.fail[node]
                while state and ch not in self.goto[state]:
                    state = self.fail[state]
                self.fail[child] = self.goto[state].get(ch, 0) if state or ch in self.goto[0] else 0
                if self.fail[child] == child:
                    self.fail[child] = 0
                out[child] |= out[self.fail[child]]   # inherit suffix matches
                queue.append(child)

        self.out = [frozenset(s) for s in out]

    def matched(self, text):
        """Every pattern that occurs anywhere in `text`, as a set."""
        if self._empty:
            return frozenset()
        found = set()
        goto, fail, out = self.goto, self.fail, self.out
        node = 0
        for ch in text:
            while node and ch not in goto[node]:
                node = fail[node]
            node = goto[node].get(ch, 0)
            if out[node]:
                found |= out[node]
        return found

    def finditer(self, text):
        """Every occurrence as (start, end, pattern), in end-position order.

        `matched()` answers "which terms are present"; the guards also need
        "where", to tell a real hit from one sitting inside a longer term.
        """
        if self._empty:
            return
        goto, fail, out = self.goto, self.fail, self.out
        node = 0
        for i, ch in enumerate(text):
            while node and ch not in goto[node]:
                node = fail[node]
            node = goto[node].get(ch, 0)
            for pattern in out[node]:
                yield i + 1 - len(pattern), i + 1, pattern

    def __len__(self):
        return len(self.goto)
